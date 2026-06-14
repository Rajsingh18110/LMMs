import os
import glob
import urllib.request
from bs4 import BeautifulSoup
from lmms.backend.memory.embeddings.faiss_provider import VectorDB

class RAGTool:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        if self.workspace_id and self.workspace_id != "None":
            self.db = VectorDB(workspace_id)
        else:
            self.db = None

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> list:
        words = text.split()
        chunks = []
        current_chunk = []
        current_len = 0
        for word in words:
            current_len += len(word) + 1
            if current_len > chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_len = len(word) + 1
            else:
                current_chunk.append(word)
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def ingest_file(self, path: str) -> str:
        if not self.db:
            return "Error: No active workspace to save vectors into."
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = self._chunk_text(content)
            metas = [{"source": path, "type": "file", "chunk": i} for i in range(len(chunks))]
            self.db.add_texts(chunks, metas)
            return f"Successfully ingested {len(chunks)} chunks from {path}"
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    def ingest_directory(self, path: str) -> str:
        if not self.db:
            return "Error: No active workspace."
        try:
            total_chunks = 0
            files_read = 0
            for root, _, files in os.walk(path):
                # Skip massive hidden dirs like .git, node_modules, .venv
                if any(ignored in root for ignored in ["/.git", "/node_modules", "/.venv", "/__pycache__"]):
                    continue
                for file in files:
                    filepath = os.path.join(root, file)
                    if any(filepath.endswith(ext) for ext in [".txt", ".md", ".json", ".py", ".csv", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h"]):
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                content = f.read()
                            chunks = self._chunk_text(content)
                            metas = [{"source": filepath, "type": "file", "chunk": i} for i in range(len(chunks))]
                            self.db.add_texts(chunks, metas)
                            total_chunks += len(chunks)
                            files_read += 1
                        except:
                            pass
            return f"Successfully ingested {total_chunks} chunks from {files_read} files in {path}"
        except Exception as e:
            return f"Error reading directory {path}: {str(e)}"

    def ingest_url(self, url: str) -> str:
        if not self.db:
            return "Error: No active workspace."
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read()
            soup = BeautifulSoup(html, 'html.parser')
            # Extract text from p, h1, h2, h3, li, etc.
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'article'])
            content = " ".join([elem.get_text(separator=' ', strip=True) for elem in text_elements])
            if not content.strip():
                content = soup.get_text(separator=' ', strip=True)
                
            chunks = self._chunk_text(content)
            metas = [{"source": url, "type": "url", "chunk": i} for i in range(len(chunks))]
            self.db.add_texts(chunks, metas)
            return f"Successfully scraped and ingested {len(chunks)} chunks from {url}"
        except Exception as e:
            return f"Error scraping url {url}: {str(e)}"

    def search(self, query: str, k: int = 5) -> str:
        if not self.db:
            return "Error: No active workspace. Cannot search."
        try:
            results = self.db.search(query, k=k)
            if not results:
                return "No relevant context found in RAG memory."
            
            out = []
            for r in results:
                src = r.get('source', 'Unknown')
                text = r.get('text', '')
                dist = r.get('distance', 0)
                out.append(f"--- Source: {src} (Dist: {dist:.2f}) ---\n{text}\n")
            return "\n".join(out)
        except Exception as e:
            return f"Error searching vector db: {str(e)}"
