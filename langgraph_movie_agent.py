import json
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict
from langgraph.config import get_stream_writer
from langgraph.graph import (
    StateGraph,
    START,
    END,
)
import operator
from typing import Annotated
from langgraph.errors import GraphRecursionError

from movie_agent import (
    client,
    tool_schemas,
    execute_tool,

    build_long_term_memory_message,
    build_memory_message,
    update_short_term_memory,
    SYSTEM_MESSAGE,
    get_session_messages,
    conversation_store,
)
checkpointer = InMemorySaver()

# =====================================
# 1. 定义整个 Agent 的 State
# =====================================

class MovieAgentState(TypedDict):
    messages: Annotated[
        list,
        operator.add
    ]

    session_id: str
    user_id: str

    pending_tool_calls: list


# =====================================
# 2. 把 DeepSeek 返回消息转换成普通 dict
# =====================================

def convert_assistant_message(message):

    result = {
        "role": "assistant",
        "content": message.content,
    }

    if message.tool_calls:

        result["tool_calls"] = []

        for tool_call in message.tool_calls:

            result["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",

                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )

    return result


# =====================================
# 3. LLM Node
# =====================================

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
            session_id
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
        client.chat.completions.create(
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

# =====================================
# 4. Router
# =====================================

def route_after_llm(
    state: MovieAgentState
):

    tool_calls = state[
        "pending_tool_calls"
    ]

    if tool_calls:

        print(
            "模型决定调用工具 → Tool Node"
        )

        return "tools"

    print(
        "模型已经生成最终回答 → END"
    )

    return "end"


# =====================================
# 5. Tool Node
# =====================================

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
            session_id=session_id,
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
# =====================================
# 6. 构建 Graph
# =====================================

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


# =====================================
# 7. 对外提供调用函数
# =====================================

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
                session_id,
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

# =====================================
# 8. 本地测试
# =====================================

def test_graph_stream(
    user_input: str,
    session_id: str,
    user_id: str,
):

    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": user_input,
            }
        ],

        "session_id": session_id,
        "user_id": user_id,
        "pending_tool_calls": [],
    }

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    for mode, chunk in movie_graph.stream(
            initial_state,
            config=config,
            stream_mode=[
                "updates",
                "custom",
            ],
    ):
        print(
            "\n模式：",
            mode
        )

        print(
            "数据：",
            chunk
        )


def stream_movie_agent(
    user_input: str,
    session_id: str,
    user_id: str,
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
                session_id,
        }
    }

    for mode, chunk in movie_graph.stream(

        initial_state,

        config=config,

        stream_mode=[
            "updates",
            "custom",
        ],
    ):

        if mode != "custom":
            continue

        yield (
            json.dumps(
                chunk,
                ensure_ascii=False,
            )
            + "\n"
        )








if __name__ == "__main__":

    test_graph_stream(
        user_input="推荐一部9分以上的电影",
        session_id="stream-test-001",
        user_id="user-001",
    )
