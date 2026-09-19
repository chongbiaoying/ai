import os
import json

from dotenv import load_dotenv
from openai import OpenAI

from schemas import MovieRecommendation


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def recommend_movie(prompt: str) -> MovieRecommendation:
    messages = [
        {
            "role": "system",
            "content": """
你是一个电影推荐助手。

请根据用户的需求推荐一部电影。

必须使用 JSON 格式返回：

{
    "movie_name": "电影名称",
    "score": 评分,
    "reason": "推荐理由"
}
""",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    response = client.chat.completions.create(
        model="deepseek-v4.1-flash",
        messages=messages,
        response_format={
            "type": "json_object"
        },
    )

    content = response.choices[0].message.content

    data = json.loads(content)

    movie = MovieRecommendation.model_validate(data)

    return movie