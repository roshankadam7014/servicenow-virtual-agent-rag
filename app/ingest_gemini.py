import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=True

)

print("BASE_DIR:", BASE_DIR)
print("ENV FILE EXISTS:", (BASE_DIR / ".env").exists())
print("GEMINI KEY LOADED:", bool(os.getenv("GEMINI_API_KEY")))


KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge_base"
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

GEMINI_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 384


def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + 180, len(words))
        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        if end == len(words):
            break

        start = end - 30

    return chunks


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    print("API key available inside main:", bool(api_key))
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=api_key)
    documents = []

    for path in KNOWLEDGE_DIR.glob("*.txt"):
        text = path.read_text(encoding="utf-8")

        for number, chunk in enumerate(chunk_text(text)):
            documents.append({
                "text": chunk,
                "source": path.name,
                "chunk": number
            })

    if not documents:
        raise RuntimeError("No TXT knowledge documents found.")

    embeddings = []

    for document in documents:
        response = client.models.embed_content(
            model=GEMINI_MODEL,
            contents=document["text"],
            config={
                "output_dimensionality": EMBEDDING_DIMENSION
            }
        )

        embeddings.append(response.embeddings[0].values)

    embeddings = np.asarray(embeddings, dtype="float32")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)

    if np.any(norms == 0):
        raise ValueError("Gemini generated a zero embedding.")

    embeddings = embeddings / norms

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    np.save(VECTOR_DIR / "gemini_embeddings.npy", embeddings)

    with open(
        VECTOR_DIR / "gemini_metadata.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(documents, file, ensure_ascii=False, indent=2)

    print(f"Gemini index created: {len(documents)} chunks")
    print(f"Embedding dimension: {embeddings.shape[1]}")


if __name__ == "__main__":
    main()