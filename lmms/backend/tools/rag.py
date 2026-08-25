import os
import glob
import urllib.request
from bs4 import BeautifulSoup
from lmms.backend.memory.embeddings.faiss_provider import VectorDB
from concurrent.futures import ProcessPoolExecutor

_process_pool = None

def _crawl4ai_worker(url: str) -> str:
    import asyncio
    from crawl4ai import AsyncWebCrawler
    async def _crawl():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url)
            return result.markdown
    return asyncio.run(_crawl())

class RAGTool:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        if self.workspace_id and self.workspace_id != "None":
            self.db = VectorDB(workspace_id)
        else:
            self.db = None

    def _get_token_count(self, text: str) -> int:
        try:
            from lmms.engine.manager import engine_manager
            if engine_manager.runtime and hasattr(engine_manager.runtime, '_models') and engine_manager.runtime._models:
                model_name = list(engine_manager.runtime._models.keys())[0]
                model = engine_manager.runtime._models[model_name]["model"]
                return len(model.tokenize(text.encode('utf-8')))
        except Exception:
            pass
        return max(1, len(text) // 4)

    def _chunk_text(self, text: str, max_tokens: int = 250) -> list:
        # Fast chunking using character heuristic ~ 4 chars per token
        chunk_size_chars = max_tokens * 4
        words = text.split()
        chunks = []
        current_chunk = []
        current_len = 0
        for word in words:
            word_len = len(word) + 1
            if current_len + word_len > chunk_size_chars:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_len = word_len
            else:
                current_chunk.append(word)
                current_len += word_len
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
            global _process_pool
            if _process_pool is None:
                _process_pool = ProcessPoolExecutor(max_workers=1)
                
            try:
                future = _process_pool.submit(_crawl4ai_worker, url)
                content = future.result(timeout=60)
            except Exception as worker_exc:
                return f"Error: Crawl4AI worker failed to process {url}. Details: {str(worker_exc)}"

            if not content or not content.strip():
                return f"Error: No content could be extracted from {url}."
                
            chunks = self._chunk_text(content)
            metas = [{"source": url, "type": "url", "chunk": i} for i in range(len(chunks))]
            self.db.add_texts(chunks, metas)
            return f"Successfully scraped and ingested {len(chunks)} chunks from {url}"
        except Exception as e:
            return f"Error scraping url {url}: {str(e)}"

    def search(self, query: str, k: int = 5, max_tokens: int = None) -> str:
        if not self.db:
            return "Error: No active workspace. Cannot search."
        try:
            results = self.db.search(query, k=k)
            if not results:
                return "No relevant context found in RAG memory."
            
            out = []
            total_tokens = 0
            for r in results:
                src = r.get('source', 'Unknown')
                text = r.get('text', '')
                dist = r.get('distance', 0)
                
                chunk_str = f"--- Source: {src} (Dist: {dist:.2f}) ---\n{text}\n"
                tokens = self._get_token_count(chunk_str)
                
                if max_tokens is not None:
                    if total_tokens + tokens > max_tokens:
                        remaining = max_tokens - total_tokens
                        if remaining > 50:
                            allowed_chars = remaining * 4
                            chunk_str = chunk_str[:allowed_chars] + "...[truncated to fit budget]\n"
                            out.append(chunk_str)
                        break
                        
                out.append(chunk_str)
                total_tokens += tokens
                
            return "\n".join(out)
        except Exception as e:
            return f"Error searching vector db: {str(e)}"
