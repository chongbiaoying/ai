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


tool_schemas = [
    {
        "type": "function",
        "function": {
            "name": "get_movie_by_id",
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
    },

    {
        "type": "function",
        "function": {
            "name": "search_movies_db",
            "description": "根据关键词搜索电影，可以搜索电影名称或电影类型",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "电影名称或电影类型关键词",
                    }
                },
                "required": ["keyword"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "filter_movies_db",
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
                        "description": "最低评分，例如9表示评分至少9分",
                    },
                    "year": {
                        "type": "integer",
                        "description": "电影上映年份，例如1994",
                    },
                },
                "required": [],
            },
        },
    },
]

tool_map = {
        "get_movie_by_id": get_movie_by_id,
        "search_movies_db": search_movies_db,
        "filter_movies_db": filter_movies_db,
    }

def execute_tool(tool_call):
    tool_name = tool_call.function.name

    try:
        arguments = json.loads(
            tool_call.function.arguments
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"工具参数解析失败：{error}"
        )

    tool_function = tool_map.get(
        tool_name
    )

    if tool_function is None:
        raise ValueError(
            f"未知工具：{tool_name}"
        )

    print(
        "模型选择工具：",
        tool_name
    )

    print(
        "工具参数：",
        arguments
    )

    tool_result = tool_function(
        **arguments
    )

    print(
        "工具执行结果：",
        tool_result
    )

    return tool_result

def run_movie_agent(
    user_input: str,
    max_steps: int = 5,
) -> str:

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个电影助手。"
                "当需要查询真实电影数据时，请使用提供的工具。"
                "不要编造数据库中不存在的信息。"
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
            tools=tools,
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


answer = run_movie_agent(
    "帮我找1994年评分9分以上的剧情电影"
)

print()
print("最终回答：")
print(answer)
