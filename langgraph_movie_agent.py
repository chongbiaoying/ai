import json
import logging
import operator
from typing import Annotated

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.errors import GraphRecursionError
from langgraph.graph import (
    StateGraph,
    START,
    END,
)
from typing_extensions import TypedDict

from movie_agent import (
    get_client,
    tool_schemas,
    execute_tool,

    build_long_term_memory_message,
    build_memory_message,
    update_short_term_memory,
    SYSTEM_MESSAGE,
)

logger = logging.getLogger(__name__)
checkpointer = InMemorySaver()


def session_key(user_id: str, session_id: str) -> str:
    """Scope process-local conversation state to a user and a session."""
    return json.dumps([user_id, session_id], ensure_ascii=False)

class MovieAgentState(TypedDict):
    messages: Annotated[
        list,
        operator.add
    ]

    session_id: str
    user_id: str

    pending_tool_calls: list


def llm_node(
    state: MovieAgentState
):

    writer = get_stream_writer()

    writer(
        {
            "type": "status",
            "message":
                "AI 正在分析问题",
        }
    )

    user_id = state["user_id"]
    session_id = state["session_id"]

    # =========================
    # 构建 Context
    # =========================

    context_messages = [
        SYSTEM_MESSAGE.copy()
    ]

    long_term_memory_message = (
        build_long_term_memory_message(
            user_id
        )
    )

    short_term_memory_message = (
        build_memory_message(
            session_key(user_id, session_id)
        )
    )

    if long_term_memory_message is not None:

        context_messages.append(
            long_term_memory_message
        )

    if short_term_memory_message is not None:

        context_messages.append(
            short_term_memory_message
        )

    context_messages.extend(
        state["messages"]
    )

    # =========================
    # DeepSeek Streaming
    # =========================

    response_stream = (
        get_client().chat.completions.create(
            model="deepseek-flash",
            messages=context_messages,
            tools=tool_schemas,

            # 核心
            stream=True,
        )
    )

    # 最终文本
    content_parts = []

    # 流式 Tool Call 缓冲区
    tool_call_buffers = {}

    # =========================
    # 不断接收 DeepSeek chunk
    # =========================

    for chunk in response_stream:

        if not chunk.choices:
            continue

        choice = chunk.choices[0]

        delta = choice.delta

        # -------------------------
        # 普通文本
        # -------------------------

        if delta.content:

            content_parts.append(
                delta.content
            )

            # 立刻发送给 LangGraph Stream
            writer(
                {
                    "type": "token",
                    "content":
                        delta.content,
                }
            )

        # -------------------------
        # Tool Calling
        # -------------------------

        if delta.tool_calls:

            for tool_call_part in (
                delta.tool_calls
            ):

                index = (
                    tool_call_part.index
                )

                # 第一次见到这个 Tool Call
                if index not in (
                    tool_call_buffers
                ):

                    tool_call_buffers[
                        index
                    ] = {
                        "id": "",
                        "type": "function",

                        "function": {
                            "name": "",
                            "arguments": "",
                        },
                    }

                buffer = (
                    tool_call_buffers[
                        index
                    ]
                )

                # id
                if tool_call_part.id:

                    buffer["id"] = (
                        tool_call_part.id
                    )

                # type
                if tool_call_part.type:

                    buffer["type"] = (
                        tool_call_part.type
                    )

                function_part = (
                    tool_call_part.function
                )

                if function_part:

                    # function name
                    if function_part.name:

                        buffer[
                            "function"
                        ][
                            "name"
                        ] += (
                            function_part.name
                        )

                    # arguments
                    if (
                        function_part.arguments
                    ):

                        buffer[
                            "function"
                        ][
                            "arguments"
                        ] += (
                            function_part.arguments
                        )

    # =========================
    # Streaming结束
    # =========================

    full_content = "".join(
        content_parts
    )

    tool_calls = [
        tool_call_buffers[index]

        for index in sorted(
            tool_call_buffers
        )
    ]

    assistant_message = {
        "role": "assistant",
        "content":
            full_content or None,
    }

    if tool_calls:

        assistant_message[
            "tool_calls"
        ] = tool_calls

    return {
        "messages": [
            assistant_message
        ],

        "pending_tool_calls":
            tool_calls,
    }

def route_after_llm(
    state: MovieAgentState
):

    tool_calls = state[
        "pending_tool_calls"
    ]

    if tool_calls:

        return "tools"

    return "end"


def tool_node(
    state: MovieAgentState
):

    writer = get_stream_writer()

    user_id = state["user_id"]
    session_id = state["session_id"]

    tool_calls = state[
        "pending_tool_calls"
    ]

    tool_messages = []

    for tool_call in tool_calls:

        tool_name = (
            tool_call[
                "function"
            ][
                "name"
            ]
        )

        arguments_json = (
            tool_call[
                "function"
            ][
                "arguments"
            ]
        )

        writer(
            {
                "type":
                    "tool_start",

                "tool":
                    tool_name,

                "message":
                    f"正在执行工具：{tool_name}",
            }
        )

        tool_result = execute_tool(
            tool_name=tool_name,
            arguments_json=
                arguments_json,
            user_id=user_id,
        )

        update_short_term_memory(
            session_id=session_key(user_id, session_id),
            tool_result=tool_result,
        )

        writer(
            {
                "type":
                    "tool_end",

                "tool":
                    tool_name,

                "success":
                    tool_result[
                        "success"
                    ],
            }
        )

        tool_messages.append(
            {
                "role": "tool",

                "tool_call_id":
                    tool_call["id"],

                "content":
                    json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
            }
        )

    return {
        "messages":
            tool_messages,

        "pending_tool_calls": [],
    }
builder = StateGraph(
    MovieAgentState
)


builder.add_node(
    "llm",
    llm_node,
)


builder.add_node(
    "tools",
    tool_node,
)


# START → LLM

builder.add_edge(
    START,
    "llm",
)


# LLM → Tool 或 END

builder.add_conditional_edges(
    "llm",

    route_after_llm,

    {
        "tools": "tools",
        "end": END,
    },
)


# Tool执行完
# 再回到LLM

builder.add_edge(
    "tools",
    "llm",
)


movie_graph = builder.compile(checkpointer=checkpointer)


def run_movie_graph_agent(
    user_input: str,
    session_id: str,
    user_id: str,
    max_steps: int = 5,
):

    initial_state = {

        "messages": [
            {
                "role": "user",
                "content": user_input,
            }
        ],

        "session_id":
            session_id,

        "user_id":
            user_id,

        "pending_tool_calls": [],
    }

    config = {

        "configurable": {

            "thread_id":
                session_key(user_id, session_id),
        },

        "recursion_limit":
            max_steps * 2 + 3,
    }

    try:

        final_state = (
            movie_graph.invoke(
                initial_state,
                config=config,
            )
        )

    except GraphRecursionError:

        raise RuntimeError(
            f"Agent执行超过最大轮数：{max_steps}"
        )

    last_message = (
        final_state[
            "messages"
        ][-1]
    )

    return last_message[
        "content"
    ]

def stream_movie_agent(
    user_input: str,
    session_id: str,
    user_id: str,
):
    logger.info("流式 AI 请求开始 session_id=%s", session_id)

    initial_state = {

        "messages": [
            {
                "role": "user",
                "content": user_input,
            }
        ],

        "session_id":
            session_id,

        "user_id":
            user_id,

        "pending_tool_calls": [],
    }

    config = {

        "configurable": {

            "thread_id":
                session_key(user_id, session_id),
        }
    }

    try:
        for mode, chunk in movie_graph.stream(
            initial_state,
            config=config,
            stream_mode=["custom"],
        ):
            if mode == "custom":
                yield json.dumps(chunk, ensure_ascii=False) + "\n"
    except Exception:
        logger.exception("流式 Agent 执行失败 session_id=%s", session_id)
        yield json.dumps(
            {"type": "error", "message": "AI Agent服务暂时不可用"},
            ensure_ascii=False,
        ) + "\n"
    else:
        logger.info("流式 AI 请求完成 session_id=%s", session_id)
        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
