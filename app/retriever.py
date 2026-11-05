
import json
import os
from pathlib import Path


import numpy as np

from dotenv import load_dotenv
from google import genai


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "data" / "vector_store"

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class KnowledgeRetriever:

    def __init__(self):
        self.embedding_provider = os.getenv(
            "LLM_PROVIDER", "local"
        ).lower()

        if self.embedding_provider == "gemini":
            print("Initializing Gemini API...")

            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise ValueError("GEMINI_API_KEY is missing.")

            self.gemini_client = genai.Client(api_key=api_key)
            self.model = None

            embeddings_path = VECTOR_DIR / "gemini_embeddings.npy"
            metadata_path = VECTOR_DIR / "gemini_metadata.json"

            if not embeddings_path.exists():
                raise FileNotFoundError(
                    f"Gemini embeddings not found: {embeddings_path}"
                )

            if not metadata_path.exists():
                raise FileNotFoundError(
                    f"Gemini metadata not found: {metadata_path}"
                )

            self.embeddings = np.load(embeddings_path).astype("float32")

            with open(metadata_path, "r", encoding="utf-8") as file:
                self.metadata = json.load(file)

            self.documents = self.metadata

            if len(self.embeddings) != len(self.documents):
                raise ValueError(
                    "Gemini embeddings count does not match metadata count."
                )

            if self.embeddings.ndim != 2 or self.embeddings.shape[1] != 384:
                raise ValueError(
                    "Gemini embeddings must have 384 dimensions."
                )

        elif self.embedding_provider == "local":
            print("Loading local embedding model...")

            import faiss
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.gemini_client = None

            index_path = VECTOR_DIR / "knowledge.index"
            metadata_path = VECTOR_DIR / "metadata.json"

            if not index_path.exists():
                raise FileNotFoundError(
                    f"FAISS index not found: {index_path}"
                )

            if not metadata_path.exists():
                raise FileNotFoundError(
                    f"Metadata not found: {metadata_path}"
                )

            self.index = faiss.read_index(str(index_path))

            with open(metadata_path, "r", encoding="utf-8") as file:
                self.metadata = json.load(file)

            self.documents = self.metadata

            if self.index.ntotal != len(self.documents):
                raise ValueError(
                    "FAISS index count does not match metadata count."
                )

        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.embedding_provider}"
            )

        print(f"Retriever loaded: {len(self.metadata)} chunks")

    def search(self, question: str, top_k: int = 3) -> list[dict]:

        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if self.embedding_provider == "local":

            query_embedding = self.model.encode(
                [question],
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            results_count = min(top_k, self.index.ntotal)

            if results_count == 0:
                return []

            scores, indices = self.index.search(
                query_embedding.astype("float32"),
                results_count
            )

            ranked_results = [
                (int(idx), float(score))
                for score, idx in zip(scores[0], indices[0])
                if idx >= 0
            ]

        else:

            response = self.gemini_client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=question,
                config={"output_dimensionality": 384}
            )

            query_embedding = np.asarray(
                response.embeddings[0].values,
                dtype="float32"
            )

            norm = np.linalg.norm(query_embedding)

            if norm == 0:
                raise ValueError("Gemini returned a zero embedding.")

            query_embedding /= norm

            similarities = self.embeddings @ query_embedding

            top_indices = np.argsort(similarities)[::-1][
                :min(top_k, len(self.embeddings))
            ]

            ranked_results = [
                (int(idx), float(similarities[idx]))
                for idx in top_indices
            ]

        results = []

        for idx, score in ranked_results:

            document = self.documents[idx]

            results.append({
                "text": document["text"],
                "source": document["source"],
                "chunk": document["chunk"],
                "score": score
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
