import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


class MovieRecommendation(BaseModel):
    movie_name: str = Field(
        min_length=1,
        description="推荐电影名称",
    )

    score: float = Field(
        ge=0,
        le=10,
        description="电影评分",
    )

    reason: str = Field(
        min_length=1,
        description="推荐理由",
    )

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

messages = [
    {
        "role": "system",
        "content": """
你是一个电影信息提取助手。
请始终使用 JSON 格式回答。

返回格式：
{
    "movie_name": "电影名称",
    "score": 评分,
    "reason": "推荐理由"
}
""",
    },
    {
        "role": "user",
        "content": input("请输入你的电影需求："),
    },
]

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    response_format={
        "type": "json_object"
    },
)

content = response.choices[0].message.content

data = json.loads(content)
movie = MovieRecommendation.model_validate(data)
print("名字：", movie.movie_name)
print("评分：", movie.score)
print("推荐理由：", movie.reason)