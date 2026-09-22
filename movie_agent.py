import os
import json
from rag_service import retrieve

from dotenv import load_dotenv
from openai import OpenAI

from database import (
    get_movie_by_id,
    search_movies_db,
    filter_movies_db,
    get_user_memory,
    update_user_memory,
)


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)


def search_knowledge_base(
    query: str,
):
    results = retrieve(
        query=query,
        top_k=3,
    )

    return results


tool_registry = {
    "get_movie_by_id": {
        "function": get_movie_by_id,
        "description": "根据电影ID查询电影详细信息",
        "parameters": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "需要查询的电影ID",
                }
            },
            "required": ["movie_id"],
        },
    },

    "search_movies_db": {
        "function": search_movies_db,
        "description": "根据关键词搜索电影名称或电影类型",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "电影名称或类型关键词",
                }
            },
            "required": ["keyword"],
        },
    },

    "filter_movies_db": {
        "function": filter_movies_db,
        "description": "根据关键词、最低评分和上映年份筛选电影",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "电影名称或类型关键词",
                },
                "min_score": {
                    "type": "number",
                    "description": "最低评分",
                },
                "year": {
                    "type": "integer",
                    "description": "上映年份",
                },
            },
            "required": [],
        },
    },

    "update_user_memory": {
        "function": update_user_memory,

        "description": (
            "保存或更新用户的长期电影偏好。"
            "只有当用户明确表达长期、稳定的偏好时才使用，"
            "例如‘我喜欢科幻片’、"
            "‘以后优先给我推荐8.5分以上的电影’。"
            "不要因为用户临时查询某种电影就修改长期记忆。"
        ),

        "parameters": {
            "type": "object",

            "properties": {
                "favorite_type": {
                    "type": "string",
                    "description": (
                        "用户长期偏好的电影类型，"
                        "例如科幻、剧情、喜剧"
                    ),
                },

                "preferred_min_score": {
                    "type": "number",
                    "description": (
                        "用户长期偏好的最低电影评分，"
                        "范围0到10"
                    ),
                },
            },

            "required": [],
        },

        "inject_user_id": True,
    },

    "search_knowledge_base": {

        "function":
            search_knowledge_base,

        "description": (
            "从项目知识库中检索与问题相关的资料。"
            "适合回答项目设计、RAG、Agent、"
            "Tool Calling、Memory、Context 等"
            "知识和文档类问题。"
            "如果用户是在查询电影名称、评分、年份、"
            "电影类型等真实电影数据，"
            "不要使用这个工具，应使用电影数据库工具。"
        ),

        "parameters": {
            "type": "object",

            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "需要在知识库中检索的问题"
                    ),
                }
            },

            "required": [
                "query"
            ],
        },
    },
}

tool_schemas = []
for tool_name, tool_info in tool_registry.items():
    tool_schemas.append(
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_info["description"],
                "parameters": tool_info["parameters"],
            },
        }
    )



short_term_memory_store = {}




def build_long_term_memory_message(
    user_id: str
):
    memory = get_user_memory(user_id)

    if memory is None:
        return None

    parts = []

    favorite_type = memory.get(
        "favorite_type"
    )

    preferred_min_score = memory.get(
        "preferred_min_score"
    )

    if favorite_type:
        parts.append(
            f"用户长期偏好的电影类型是：{favorite_type}"
        )

    if preferred_min_score is not None:
        parts.append(
            f"用户通常偏好评分不低于 {preferred_min_score} 的电影"
        )

    if not parts:
        return None

    return {
        "role": "system",
        "content": (
            "用户长期记忆："
            + "；".join(parts)
        ),
    }

def build_memory_message(
    session_id: str
):
    memory = get_short_term_memory(
        session_id
    )

    current_movie = memory.get(
        "current_movie"
    )

    if current_movie is None:
        return None

    return {
        "role": "system",
        "content": (
            "当前会话的短期记忆："
            f"最近正在讨论的电影是《{current_movie}》。"
        ),
    }

def update_short_term_memory(
    session_id: str,
    tool_result: dict,
):
    if not tool_result.get("success"):
        return

    data = tool_result.get("data")

    memory = get_short_term_memory(
        session_id
    )

    if isinstance(data, dict):
        movie_name = data.get("name")

        if movie_name:
            memory["current_movie"] = movie_name

    elif isinstance(data, list):
        if len(data) == 1:
            movie_name = data[0].get("name")

            if movie_name:
                memory["current_movie"] = movie_name

def get_short_term_memory(
    session_id: str
):
    if session_id not in short_term_memory_store:
        short_term_memory_store[session_id] = {
            "current_movie": None
        }

    return short_term_memory_store[session_id]

def get_session_messages(session_id: str):
    if session_id not in conversation_store:
        conversation_store[session_id] = [
            SYSTEM_MESSAGE.copy()
        ]

    return conversation_store[session_id]

def execute_tool(
    tool_call,
    user_id: str,
):
    tool_name = tool_call.function.name

    try:
        arguments = json.loads(
            tool_call.function.arguments
        )
    except json.JSONDecodeError as error:
        return {
            "success": False,
            "error": f"工具参数解析失败：{error}",
        }

    tool_info = tool_registry.get(tool_name)

    if tool_info is None:
        return {
            "success": False,
            "error": f"未知工具：{tool_name}",
        }

    tool_function = tool_info["function"]

    if tool_info.get("inject_user_id"):
        arguments["user_id"] = user_id

    try:
        tool_result = tool_function(
            **arguments
        )

    except Exception as error:
        return {
            "success": False,
            "error": f"工具执行失败：{error}",
        }

    if tool_result is None or tool_result == []:
        return {
            "success": False,
            "error": "没有找到符合条件的数据",
        }

    return {
        "success": True,
        "data": tool_result,
    }


SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "你是一个电影助手。"

        "需要真实电影数据时必须使用工具，"
        "不要编造数据库中不存在的信息。"

        "如果工具返回 success=false，"
        "请根据 error 字段向用户说明情况，"
        "不要假装查询成功。"

        "当用户明确表达长期、稳定的电影偏好时，"
        "例如‘我喜欢科幻片’、"
        "‘以后优先推荐剧情片’、"
        "‘我通常只看8分以上的电影’，"
        "可以调用 update_user_memory 保存长期记忆。"

        "如果用户只是临时查询某种电影，"
        "不要把它当作长期偏好保存。"
        
        "如果用户询问项目设计、Agent、RAG、"
        "Tool Calling、Memory、Context 等"
        "知识库中的技术资料，"
        "可以使用 search_knowledge_base 工具检索资料。"
        
        "查询电影评分、年份、类型、电影名称等真实电影数据时，"
        "应优先使用电影数据库工具，"
        "不要使用知识库工具代替电影数据库查询。"
    ),
}

conversation_store = {}

def run_movie_agent(
    user_input: str,
    session_id: str,
    user_id: str,
    max_steps: int = 5,
) -> str:

    messages = get_session_messages(
        session_id
    )

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    for step in range(max_steps):

        context_messages = messages.copy()

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

        insert_index = 1

        if long_term_memory_message is not None:
            context_messages.insert(
                insert_index,
                long_term_memory_message,
            )
            insert_index += 1

        if short_term_memory_message is not None:
            context_messages.insert(
                insert_index,
                short_term_memory_message,
            )

        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=context_messages,
            tools=tool_schemas,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                }
            )

            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:

            tool_result = execute_tool(
                tool_call,
                user_id=user_id,
            )

            update_short_term_memory(
                session_id=session_id,
                tool_result=tool_result,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
                }
            )

    raise RuntimeError(
        f"Agent执行超过最大轮数：{max_steps}"
    )

