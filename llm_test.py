import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

messages = [
    {
        "role": "system",
        "content": "你是一个耐心、通俗易懂的编程学习助手。",
    }
]

while True:
    user_input = input("你：").strip()

    if user_input == "退出":
        break
    if not user_input:
        continue
    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=True,
    )
    print("AI：", end="", flush=True)
    assistant_message = ""
    for chunk in response:
        content=chunk.choices[0].delta.content
        if content is not None:
            print(content, end="", flush=True)
            assistant_message += content
    print()

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )