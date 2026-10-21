"""
Retriever Module for LMMs RAG.
Performs semantic similarity search with token budget management and source attribution.
"""

from typing import List, Dict, Any, Optional
from lmms.backend.memory.embeddings.faiss_provider import VectorDB


class RAGRetriever:
    """Retrieves relevant contexts from vector memory."""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        if self.workspace_id and self.workspace_id != "None":
            self.db = VectorDB(self.workspace_id)
        else:
            self.db = None

    def search(self, query: str, k: int = 5, max_tokens: Optional[int] = None) -> str:
        """Search top-k matching documents and format nicely with sources."""
        if not self.db:
            return "Error: No active workspace. Cannot search vector database."

        try:
            results = self.db.search(query, k=k)
            if not results:
                return "No relevant context found in RAG memory."

            out = []
            total_tokens = 0

            for r in results:
                src = r.get("source", "Unknown")
                text = r.get("text", "")
                dist = r.get("distance", 0.0)

                chunk_str = f"--- Source: {src} (Score: {dist:.2f}) ---\n{text}\n"
                tokens = max(1, len(chunk_str) // 4)

                if max_tokens is not None:
                    if total_tokens + tokens > max_tokens:
                        remaining = max_tokens - total_tokens
                        if remaining > 50:
                            allowed_chars = remaining * 4
                            chunk_str = chunk_str[:allowed_chars] + "...[truncated to fit token budget]\n"
                            out.append(chunk_str)
                        break

                out.append(chunk_str)
                total_tokens += tokens

            return "\n".join(out)
        except Exception as e:
            return f"Error retrieving from vector db: {str(e)}"
