
import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class KnowledgeRetriever:
    def __init__(self):
        index_path = VECTOR_DIR / "knowledge.index"
        metadata_path = VECTOR_DIR / "metadata.json"

        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                "Knowledge index not found. Run python app/ingest.py first."
            )

        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.index = faiss.read_index(str(index_path))

        with open(metadata_path, "r", encoding="utf-8") as file:
            self.documents = json.load(file)

        if self.index.ntotal != len(self.documents):
            raise ValueError("FAISS index and metadata are inconsistent.")

        print(f"Retriever loaded: {len(self.documents)} chunks")

    def search(self, question: str, top_k: int = 3) -> list[dict]:
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_embedding = self.model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        results_count = min(top_k, self.index.ntotal)

        scores, indices = self.index.search(
            query_embedding.astype("float32"),
            results_count
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            document = self.documents[int(idx)]

            results.append({
                "text": document["text"],
                "source": document["source"],
                "chunk": document["chunk"],
                "score": float(score)
            })

        return results


if __name__ == "__main__":
    retriever = KnowledgeRetriever()

    question = input("\nAsk an IT question: ")
    results = retriever.search(question, top_k=3)

    print("\nRetrieved knowledge:")
    for i, result in enumerate(results, start=1):
        print(f"\n--- Result {i} ---")
        print(f"Source: {result['source']}")
        print(f"Similarity score: {result['score']:.4f}")
        print(result["text"])
