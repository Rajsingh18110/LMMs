import os
import pathspec
from typing import List, Dict
from lmms.backend.db.core_workspace.manager import WorkspaceManager
from lmms.backend.db.core_workspace.db import DatabaseManager

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".md": "Markdown"
}

class FileIndexer:
    """
    Lightweight incremental file indexer for Phase B.
    Indexes basic metadata (path, size, mtime, language) using pathspec to respect .gitignore.
    """
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.manager = WorkspaceManager()
        self.ws_id = self.manager.open(self.workspace_path)
        self.db = self.manager.get_db(self.ws_id)
        self.ignore_spec = self._load_gitignore()

    def _load_gitignore(self):
        gitignore_path = os.path.join(self.workspace_path, ".gitignore")
        lines = [".git/", ".lmms-id", "__pycache__/"]
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                lines.extend(f.readlines())
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)

    def _get_existing_files(self) -> Dict[str, float]:
        rows = self.db.fetchall("SELECT path, mtime FROM files")
        return {row["path"]: row["mtime"] for row in rows}

    def scan(self) -> int:
        """
        Scans the directory incrementally. Returns number of newly indexed/updated files.
        """
        existing = self._get_existing_files()
        updated_count = 0

        for root, dirs, files in os.walk(self.workspace_path):
            # Prune directories matching gitignore
            rel_root = os.path.relpath(root, self.workspace_path)
            if rel_root != ".":
                if self.ignore_spec.match_file(rel_root + "/"):
                    dirs[:] = []
                    continue

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.workspace_path)

                if self.ignore_spec.match_file(rel_path):
                    continue

                try:
                    stat = os.stat(abs_path)
                    mtime = stat.st_mtime
                    size = stat.st_size

                    if rel_path in existing and existing[rel_path] == mtime:
                        continue # Unchanged

                    language = SUPPORTED_EXTENSIONS[ext]
                    file_id = f"{self.ws_id}_{rel_path}"

                    # Insert or replace file metadata
                    self.db.execute("""
                        INSERT OR REPLACE INTO files (id, path, size, mtime, language, indexed_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (file_id, rel_path, size, mtime, language))
                    
                    updated_count += 1
                except Exception as e:
                    print(f"Error indexing {rel_path}: {e}")

        return updated_count

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    indexer = FileIndexer(path)
    count = indexer.scan()
    print(f"File Indexer completed. Indexed/Updated files: {count}")
