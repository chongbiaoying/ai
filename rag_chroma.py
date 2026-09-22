import sys
from pathlib import Path
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import (
    SentenceTransformer,
)

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

KNOWLEDGE_DIR = (
    BASE_DIR
    / "knowledge"
)

CHROMA_DIR = (
    BASE_DIR
    / "chroma_db"
)


embedding_model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

collection = (
    chroma_client.get_or_create_collection(
        name="movie_agent_knowledge",
        embedding_function=None,
        configuration={
            "hnsw": {
                "space": "cosine"
            }
        },
    )
)


def load_documents():

    documents = []

    for file_path in KNOWLEDGE_DIR.iterdir():

        if file_path.suffix not in [
            ".txt",
            ".md",
        ]:
            continue

        text = file_path.read_text(
            encoding="utf-8"
        )

        documents.append(
            {
                "source": file_path.name,
                "text": text,
            }
        )

    return documents


def split_documents(
    documents: list[dict],
):

    chunks = []

    for document in documents:

        paragraphs = document[
            "text"
        ].split("\n\n")

        for index, paragraph in enumerate(
            paragraphs
        ):

            paragraph = paragraph.strip()

            if not paragraph:
                continue

            chunks.append(
                {
                    "id": (
                        f"{document['source']}"
                        f"_{index}"
                    ),

                    "source":
                        document["source"],

                    "chunk_id":
                        index,

                    "text":
                        paragraph,
                }
            )

    return chunks


def build_knowledge_base():

    documents = load_documents()

    chunks = split_documents(
        documents
    )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    vectors = embedding_model.encode(
        texts,
        normalize_embeddings=True,
    )

    ids = []

    documents_data = []

    metadatas = []

    embeddings = []

    for chunk, vector in zip(
        chunks,
        vectors,
    ):

        ids.append(
            chunk["id"]
        )

        documents_data.append(
            chunk["text"]
        )

        metadatas.append(
            {
                "source":
                    chunk["source"],

                "chunk_id":
                    chunk["chunk_id"],
            }
        )

        embeddings.append(
            vector.tolist()
        )

    collection.upsert(
        ids=ids,
        documents=documents_data,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print(
        f"知识库建立完成，共保存 "
        f"{len(chunks)} 个 Chunk"
    )


def retrieve(
    query: str,
    top_k: int = 3,
):

    query_vector = (
        embedding_model.encode(
            query,
            normalize_embeddings=True,
        )
    )

    result = collection.query(
        query_embeddings=[
            query_vector.tolist()
        ],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    results = []

    documents = (
        result["documents"][0]
    )

    metadatas = (
        result["metadatas"][0]
    )

    distances = (
        result["distances"][0]
    )

    ids = (
        result["ids"][0]
    )

    for (
        chunk_id,
        document,
        metadata,
        distance,
    ) in zip(
        ids,
        documents,
        metadatas,
        distances,
    ):

        results.append(
            {
                "id": chunk_id,

                "text": document,

                "source":
                    metadata["source"],

                "chunk_id":
                    metadata["chunk_id"],

                "distance":
                    distance,
            }
        )

    return results


def query_loop():

    print(
        f"当前知识库共有 "
        f"{collection.count()} 个 Chunk"
    )

    while True:

        query = input(
            "\n请输入问题"
            "（输入 exit 退出）："
        )

        if query.lower() == "exit":
            break

        results = retrieve(
            query=query,
            top_k=3,
        )

        print(
            "\n检索结果：\n"
        )

        for result in results:

            print(
                f"来源："
                f"{result['source']}"
            )

            print(
                f"Chunk："
                f"{result['chunk_id']}"
            )

            print(
                f"Distance："
                f"{result['distance']:.4f}"
            )

            print(
                result["text"]
            )

            print(
                "-" * 50
            )
def build_rag_context(
    results: list[dict]
):
    context_parts = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        context_parts.append(
            f"""
[资料{index}]
来源：{result['source']}
内容：{result['text']}
""".strip()
        )

    rag_context = "\n\n".join(
        context_parts
    )

    return rag_context


def answer_with_rag(
    query: str
):
    results = retrieve(
        query=query,
        top_k=3,
    )

    rag_context = build_rag_context(
        results
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个知识库问答助手。"
                "请优先根据提供的知识库资料回答问题。"
                "如果资料不足，请明确说明资料不足，"
                "不要编造。"
            ),
        },

        {
            "role": "system",
            "content": (
                "以下是知识库检索到的资料：\n\n"
                + rag_context
            ),
        },

        {
            "role": "user",
            "content": query,
        },
    ]

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
    )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    sources = get_sources(
        results
    )

    return {
        "answer": answer,
        "sources": sources,
    }


def get_sources(
    results: list[dict]
):
    sources = []

    for result in results:
        source = result["source"]

        if source not in sources:
            sources.append(source)

    return sources




if __name__ == "__main__":

    query = input(
        "请输入问题："
    )

    result = answer_with_rag(
        query
    )

    print(
        "\n回答："
    )

    print(
        result["answer"]
    )

    print(
        "\n来源："
    )

    for source in result["sources"]:
        print(
            f"- {source}"
        )