"""
Indexer Module for LMMs RAG.
Handles text chunking, document parsing, and indexing into VectorDB.
"""

import os
import re
from typing import List, Dict, Any, Optional
from lmms.backend.memory.embeddings.faiss_provider import VectorDB


class DocumentChunker:
    """Intelligent semantic and markdown-aware chunker."""

    @staticmethod
    def chunk_markdown(text: str, max_tokens: int = 350) -> List[str]:
        """Split markdown by headers (#, ##, ###) or paragraphs, preserving context."""
        max_chars = max_tokens * 4
        # Split by header sections first
        sections = re.split(r'(?=\n#{1,4}\s)', text)
        chunks = []

        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            if len(sec) <= max_chars:
                chunks.append(sec)
            else:
                # Split large section by paragraphs
                paragraphs = sec.split("\n\n")
                current = []
                cur_len = 0
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    if cur_len + len(p) + 2 > max_chars:
                        if current:
                            chunks.append("\n\n".join(current))
                        current = [p]
                        cur_len = len(p)
                    else:
                        current.append(p)
                        cur_len += len(p) + 2
                if current:
                    chunks.append("\n\n".join(current))

        # Final pass fallback: if any chunk is still larger than max_chars, split by sentences/words
        final_chunks = []
        for c in chunks:
            if len(c) <= max_chars:
                final_chunks.append(c)
            else:
                words = c.split()
                buf = []
                b_len = 0
                for w in words:
                    if b_len + len(w) + 1 > max_chars:
                        if buf:
                            final_chunks.append(" ".join(buf))
                        buf = [w]
                        b_len = len(w)
                    else:
                        buf.append(w)
                        b_len += len(w) + 1
                if buf:
                    final_chunks.append(" ".join(buf))

        return final_chunks if final_chunks else [text[:max_chars]]


class RAGIndexer:
    """Manages document chunking and vector storage."""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        if self.workspace_id and self.workspace_id != "None":
            self.db = VectorDB(self.workspace_id)
        else:
            self.db = None
        self.chunker = DocumentChunker()

    def index_text(self, text: str, source: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Indexes raw text string into vector DB."""
        if not self.db:
            raise ValueError("No active workspace to save vectors into.")

        chunks = self.chunker.chunk_markdown(text)
        metas = []
        meta_base = metadata or {}
        for i, c in enumerate(chunks):
            m = {
                "source": source,
                "chunk_id": i,
                "total_chunks": len(chunks),
                **meta_base
            }
            metas.append(m)

        self.db.add_texts(chunks, metas)
        return len(chunks)

    def index_file(self, filepath: str) -> str:
        """Ingests and indexes a single file."""
        if not self.db:
            return "Error: No active workspace."
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            count = self.index_text(content, source=filepath, metadata={"type": "file", "filename": os.path.basename(filepath)})
            return f"Successfully indexed {count} chunks from {filepath}"
        except Exception as e:
            return f"Error indexing {filepath}: {str(e)}"

    def index_directory(self, dirpath: str) -> str:
        """Recursively ingests code and markdown files from a directory."""
        if not self.db:
            return "Error: No active workspace."
        if not os.path.isdir(dirpath):
            return f"Error: Directory not found: {dirpath}"

        allowed_exts = {".txt", ".md", ".json", ".py", ".csv", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".go", ".rs"}
        ignored_dirs = {"/.git", "/node_modules", "/.venv", "/__pycache__", "/dist", "/build"}

        total_files = 0
        total_chunks = 0

        for root, _, files in os.walk(dirpath):
            if any(ignored in root for ignored in ignored_dirs):
                continue
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in allowed_exts:
                    full_p = os.path.join(root, file)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                        if text.strip():
                            chunks = self.index_text(text, source=full_p, metadata={"type": "file", "filename": file})
                            total_chunks += chunks
                            total_files += 1
                    except Exception:
                        pass

        return f"Successfully indexed {total_chunks} chunks across {total_files} files in {dirpath}"
