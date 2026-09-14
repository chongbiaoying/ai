import os
import json

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def get_weather(city: str):
    return {
        "city": city,
        "temperature": 30,
        "weather": "晴天",
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "需要查询天气的城市名称，例如广州、北京、杭州",
                    }
                },
                "required": ["city"],
            },
        },
    }
]


messages = [
    {
        "role": "user",
        "content": "广州今天天气怎么样？",
    }
]


# 第一次请求：
# 让模型决定是否需要调用工具
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    tools=tools,
)

message = response.choices[0].message


# 查看模型是否要求调用工具
if message.tool_calls:

    tool_call = message.tool_calls[0]

    print(
        "模型决定调用工具：",
        tool_call.function.name,
    )

    print(
        "模型生成的参数：",
        tool_call.function.arguments,
    )


    # JSON字符串 → Python字典
    arguments = json.loads(
        tool_call.function.arguments
    )

    city = arguments["city"]


    # Python真正执行工具
    weather_result = get_weather(city)

    print(
        "工具真正执行后的结果：",
        weather_result,
    )


    # 保存模型刚才的tool call
    messages.append(message)


    # 把真正的工具执行结果发给模型
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(
                weather_result,
                ensure_ascii=False,
            ),
        }
    )


    # 第二次请求模型
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        tools=tools,
    )


    final_answer = (
        response
        .choices[0]
        .message
        .content
    )

    print()
    print("AI最终回答：")
    print(final_answer)


else:
    print("模型没有调用工具。")
    print(message.content)