from pathlib import Path
import chromadb
from sentence_transformers import (
    SentenceTransformer,
)

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
