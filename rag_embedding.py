from pathlib import Path

from sentence_transformers import (
    SentenceTransformer,
)


BASE_DIR = Path(__file__).resolve().parent

KNOWLEDGE_DIR = (
    BASE_DIR
    / "knowledge"
)


embedding_model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
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
                    "source": document[
                        "source"
                    ],
                    "chunk_id": index,
                    "text": paragraph,
                }
            )

    return chunks


def add_embeddings(
    chunks: list[dict],
):

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    vectors = embedding_model.encode(
        texts,
        normalize_embeddings=True,
    )

    for chunk, vector in zip(
        chunks,
        vectors,
    ):

        chunk["vector"] = vector

    return chunks


def retrieve(
    query: str,
    chunks: list[dict],
    top_k: int = 3,
):

    query_vector = embedding_model.encode(
        query,
        normalize_embeddings=True,
    )

    results = []

    for chunk in chunks:

        score = (
            query_vector
            @ chunk["vector"]
        )

        results.append(
            {
                "source": chunk["source"],
                "chunk_id": chunk[
                    "chunk_id"
                ],
                "text": chunk["text"],
                "score": float(score),
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:top_k]


if __name__ == "__main__":

    documents = load_documents()

    chunks = split_documents(
        documents
    )

    chunks = add_embeddings(
        chunks
    )

    query = input(
        "请输入问题："
    )

    results = retrieve(
        query=query,
        chunks=chunks,
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
            f"相似度："
            f"{result['score']:.4f}"
        )

        print(
            result["text"]
        )

        print(
            "-" * 50
        )