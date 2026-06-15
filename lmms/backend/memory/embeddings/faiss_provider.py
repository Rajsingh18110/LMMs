import os
import json

import numpy as np
import requests

ENGINE_URL = "http://localhost:11435"

class VectorDB:
    def __init__(self, workspace_id: str, dim: int = 4096):
        # LLaMA default embedding dim is 4096 usually, though can be different
        self.workspace_id = workspace_id
        self.dim = dim
        self.index_path = os.path.expanduser(f"~/.lmms/workspaces/{workspace_id}/index.faiss")
        self.meta_path = os.path.expanduser(f"~/.lmms/workspaces/{workspace_id}/meta.json")
        
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        if os.path.exists(self.index_path):
            import faiss
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            import faiss
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata = {}

    def get_embedding(self, text: str) -> np.ndarray:
        # Ask Engine to generate embedding
        try:
            resp = requests.post(f"{ENGINE_URL}/v1/embeddings", json={"input": text})
            resp.raise_for_status()
            data = resp.json()
            vector = data["data"][0]["embedding"]
            return np.array(vector, dtype=np.float32)
        except Exception as e:
            # Fallback mock for testing if engine is offline
            print(f"[Warning] Engine offline, generating mock embedding: {e}")
            return np.random.rand(self.dim).astype(np.float32)

    def add_texts(self, texts: list, metas: list):
        vectors = []
        start_id = len(self.metadata)
        
        for i, text in enumerate(texts):
            vec = self.get_embedding(text)
            vectors.append(vec)
            self.metadata[str(start_id + i)] = {"text": text, **metas[i]}
            
        if vectors:
            vector_matrix = np.vstack(vectors)
            self.index.add(vector_matrix)
            self.save()

    def search(self, query: str, k: int = 3) -> list:
        if self.index.ntotal == 0:
            return []
            
        q_vec = self.get_embedding(query).reshape(1, -1)
        distances, indices = self.index.search(q_vec, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                meta = self.metadata[str(idx)]
                results.append({"distance": float(distances[0][i]), **meta})
        return results

    def save(self):
        import faiss
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, 'w') as f:
            json.dump(self.metadata, f)
