from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


texts = [
    "我喜欢看科幻电影",
    "我很爱关于宇宙和未来科技的影片",
    "今天广州天气很好",
]


vectors = model.encode(
    texts,
    normalize_embeddings=True,
)

score_1=(vectors[0] @ vectors[1])
score_2=(vectors[0] @ vectors[2])

print(
    "科幻电影 vs 宇宙未来：",
    score_1,
)

print(
    "科幻电影 vs 天气：",
    score_2,
)