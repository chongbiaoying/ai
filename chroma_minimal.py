import chromadb

from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


client = chromadb.PersistentClient(
    path="./chroma_test"
)


collection = client.get_or_create_collection(
    name="test_knowledge"
)


texts = [
    "RAG 会先检索相关资料，再交给大模型回答。",
    "Tool Calling 可以让模型选择并调用外部工具。",
    "Memory 用来保存用户长期偏好和会话信息。",
]


vectors = model.encode(
    texts,
    normalize_embeddings=True,
)


collection.upsert(
    ids=[
        "chunk_1",
        "chunk_2",
        "chunk_3",
    ],

    documents=texts,

    embeddings=[
        vector.tolist()
        for vector in vectors
    ],
)


query = "怎样让 AI 查询自己的知识库？"


query_vector = model.encode(
    query,
    normalize_embeddings=True,
)


result = collection.query(
    query_embeddings=[
        query_vector.tolist()
    ],
    n_results=2,
)


print(
    result["documents"][0]
)