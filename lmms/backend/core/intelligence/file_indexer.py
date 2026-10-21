import os
import ast
import re
import json
import pathspec
from typing import List, Dict, Any, Optional
try:
    from lmms.backend.db.core_workspace.workspace.manager import WorkspaceManager
except ImportError:
    try:
        from lmms.backend.db.workspace.workspace.manager import WorkspaceManager
    except ImportError:
        WorkspaceManager = None

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".dart": "Dart",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON"
}

class FileIndexer:
    """
    Intelligent AST-powered code indexer and RepoMap generator.
    Parses symbols (classes, methods, functions, imports) and builds compact codebase maps
    for LLM coding contexts.
    """
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        try:
            self.manager = WorkspaceManager()
            self.ws_id = self.manager.open(self.workspace_path)
            self.db = self.manager.get_db(self.ws_id)
        except Exception:
            self.manager = None
            self.ws_id = "default"
            self.db = None
        self.ignore_spec = self._load_gitignore()

    def _load_gitignore(self):
        gitignore_path = os.path.join(self.workspace_path, ".gitignore")
        lines = [".git/", ".lmms-id", "__pycache__/", ".pytest_cache/", "node_modules/", "venv/", ".venv/"]
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    lines.extend(f.readlines())
            except Exception:
                pass
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)

    def extract_symbols(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Extracts top-level classes, methods, functions, and imports from code.
        """
        symbols = {"classes": [], "functions": [], "imports": []}
        if file_path.endswith(".py"):
            try:
                tree = ast.parse(content, filename=file_path)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        methods = []
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                args = [a.arg for a in item.args.args]
                                prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                                methods.append(f"{prefix}{item.name}({', '.join(args)})")
                        symbols["classes"].append({
                            "name": node.name,
                            "line": node.lineno,
                            "methods": methods
                        })
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args]
                        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                        symbols["functions"].append({
                            "name": f"{prefix}{node.name}({', '.join(args)})",
                            "line": node.lineno
                        })
                    elif isinstance(node, ast.Import):
                        for n in node.names:
                            symbols["imports"].append(n.name)
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        symbols["imports"].append(mod)
            except SyntaxError:
                pass
        elif file_path.endswith((".js", ".ts", ".dart", ".go", ".rs")):
            # Regex extraction for non-Python languages
            for line in content.splitlines():
                stripped = line.strip()
                m_class = re.match(r'^(?:export\s+)?class\s+(\w+)', stripped)
                if m_class:
                    symbols["classes"].append({"name": m_class.group(1), "methods": []})
                m_func = re.match(r'^(?:export\s+)?(?:async\s+)?(?:function|fn|func)\s+(\w+)\s*\((.*?)\)', stripped)
                if m_func:
                    symbols["functions"].append({"name": f"{m_func.group(1)}({m_func.group(2)})"})
        return symbols

    def scan(self) -> int:
        """
        Scans workspace directory incrementally, indexing metadata and AST symbols.
        """
        updated_count = 0
        existing = {}
        if self.db:
            try:
                rows = self.db.fetchall("SELECT path, mtime FROM files")
                existing = {row["path"]: row["mtime"] for row in rows}
            except Exception:
                pass

        for root, dirs, files in os.walk(self.workspace_path):
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
                        continue

                    language = SUPPORTED_EXTENSIONS[ext]
                    file_id = f"{self.ws_id}_{rel_path}"

                    # Extract symbols
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(200000)
                    symbols = self.extract_symbols(abs_path, content)

                    if self.db:
                        try:
                            self.db.execute("""
                                INSERT OR REPLACE INTO files (id, path, size, mtime, language, indexed_at)
                                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (file_id, rel_path, size, mtime, language))
                        except Exception:
                            pass
                    
                    updated_count += 1
                except Exception as e:
                    pass

        return updated_count

    def generate_repo_map(self, max_tokens: int = 1500) -> str:
        """
        Generates a concise, high-density AST RepoMap of the repository.
        Formats classes, functions, and key methods so models immediately know
        all file paths and symbol names without hallucinating.
        """
        tree_lines = ["=== REPOSITORY MAP (Symbol & Structure Graph) ==="]
        est_tokens = 20

        collected_files = []
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.pytest_cache', 'node_modules', 'venv', '.venv', 'build', 'dist')]
            rel_root = os.path.relpath(root, self.workspace_path)
            if rel_root != "." and self.ignore_spec.match_file(rel_root + "/"):
                continue

            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    abs_p = os.path.join(root, file)
                    rel_p = os.path.relpath(abs_p, self.workspace_path)
                    if not self.ignore_spec.match_file(rel_p):
                        collected_files.append((abs_p, rel_p, ext))

        for abs_p, rel_p, ext in sorted(collected_files, key=lambda x: x[1]):
            try:
                with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(100000)
                symbols = self.extract_symbols(abs_p, content)
                
                classes = symbols.get("classes", [])
                funcs = symbols.get("functions", [])
                
                if not classes and not funcs:
                    line = f"{rel_p}"
                    tree_lines.append(line)
                    est_tokens += max(1, len(line) // 4)
                else:
                    tree_lines.append(f"{rel_p}:")
                    est_tokens += max(1, len(rel_p) // 4) + 1
                    
                    for c in classes[:8]:
                        c_name = c["name"]
                        methods = c.get("methods", [])[:5]
                        m_str = f" ({', '.join(methods)})" if methods else ""
                        m_line = f"  class {c_name}{m_str}"
                        tree_lines.append(m_line)
                        est_tokens += max(1, len(m_line) // 4)
                        
                    for fn in funcs[:10]:
                        fn_name = fn["name"]
                        fn_line = f"  def {fn_name}"
                        tree_lines.append(fn_line)
                        est_tokens += max(1, len(fn_line) // 4)

                if est_tokens >= max_tokens:
                    remaining = len(collected_files) - len(tree_lines)
                    if remaining > 0:
                        tree_lines.append(f"... [{remaining} additional project files omitted for brevity]")
                    break
            except Exception:
                continue

        return "\n".join(tree_lines)


def get_default_repo_map(workspace_dir: Optional[str] = None, max_tokens: int = 1500) -> str:
    """Helper to generate a RepoMap for the active workspace."""
    ws = workspace_dir or os.getcwd()
    indexer = FileIndexer(ws)
    return indexer.generate_repo_map(max_tokens=max_tokens)
