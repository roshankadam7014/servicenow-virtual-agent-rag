
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge_base"
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 180
CHUNK_OVERLAP = 30


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import fitz

        with fitz.open(path) as pdf:
            return "\n".join(page.get_text() for page in pdf)

    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")

    return ""


def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        if end == len(words):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def main():
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    documents = []

    for path in KNOWLEDGE_DIR.rglob("*"):
        if path.suffix.lower() not in {".txt", ".pdf"}:
            continue

        text = read_document(path)

        if not text.strip():
            print(f"Skipping empty document: {path.name}")
            continue

        for number, chunk in enumerate(chunk_text(text)):
            documents.append({
                "text": chunk,
                "source": path.name,
                "chunk": number
            })

    if not documents:
        raise RuntimeError(
            f"No readable TXT or PDF documents found in {KNOWLEDGE_DIR}"
        )

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [doc["text"] for doc in documents]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(
        index,
        str(VECTOR_DIR / "knowledge.index")
    )

    with open(
        VECTOR_DIR / "metadata.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(documents, file, ensure_ascii=False, indent=2)

    print(f"Indexed {len(documents)} chunks successfully.")
    print(f"Vector dimension: {embeddings.shape[1]}")
    print(f"Saved index to: {VECTOR_DIR}")


if __name__ == "__main__":
    main()
