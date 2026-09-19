import os
import json

from dotenv import load_dotenv
from openai import OpenAI

from database import (
    get_movie_by_id,
    search_movies_db,
    filter_movies_db,
)


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

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



def execute_tool(tool_call):
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
    tool_function = tool_info["function"]
    if tool_info is None:
        return {
            "success": False,
            "error": f"未知工具：{tool_name}",
        }

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
def run_movie_agent(
    user_input: str,
    max_steps: int = 5,
) -> str:

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个电影助手。"
                "需要真实电影数据时必须使用工具。"
                "不要编造数据库中不存在的信息。"
                "如果工具返回 success=false，"
                "请根据 error 字段向用户说明情况，"
                "不要假装查询成功。"
            ),
        },
        {
            "role": "user",
            "content": user_input,
        },
    ]

    for step in range(max_steps):

        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=tool_schemas,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:
            print(
                f"第 {step + 1} 轮"
            )

            tool_result = execute_tool(tool_call)

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


