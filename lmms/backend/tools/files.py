import subprocess
import os
import shutil
import ast
import re
import difflib
from typing import Dict, Any, Optional, List

from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission
from lmms.backend.config.config import ConfigManager
from lmms.backend.tools.boundaries import require_workspace_path

config = ConfigManager()

def get_workspace_dir() -> str:
    env_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
    if env_ws and os.path.isdir(env_ws):
        return env_ws
    ws = str(config.get("workspace_dir", ""))
    if ws and os.path.isdir(ws):
        return ws
    return os.getcwd()

def enforce_boundary(path: str):
    return require_workspace_path(path, get_workspace_dir())

def _record_pre_state(path: str):
    try:
        from lmms.backend.context.checkpoint import get_turn_checkpoint_manager
        ws = get_workspace_dir()
        get_turn_checkpoint_manager(ws).record_pre_state(path)
    except Exception:
        pass

def canonical_file_read(path: str) -> Dict[str, Any]:
    resolved_path = enforce_boundary(path)
    if not os.path.exists(resolved_path):
        return {"error": f"File not found: {path}", "path": path}
    with open(resolved_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content, "path": path}

def canonical_file_write(path: str, content: str) -> Dict[str, Any]:
    resolved_path = enforce_boundary(path)
    if path.endswith(".py"):
        try:
            ast.parse(content, filename=resolved_path)
        except SyntaxError as e:
            return {
                "status": "error",
                "error": f"SyntaxError on line {e.lineno}: {e.msg}. File was NOT saved.",
                "path": path
            }
    _record_pre_state(resolved_path)
    os.makedirs(os.path.dirname(os.path.abspath(resolved_path)), exist_ok=True)
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "success", "path": path}

def canonical_view_file_outline(path: str) -> Dict[str, Any]:
    ft = FileTool()
    res = ft.view_file_outline(path)
    return {"outline": res, "path": path}

def canonical_read_file_lines(path: str, start_line: int, end_line: int) -> Dict[str, Any]:
    ft = FileTool()
    res = ft.read_file_lines(path, start_line, end_line)
    return {"lines": res, "path": path}

def canonical_replace_in_file(path: str, old_code: str, new_code: str) -> Dict[str, Any]:
    ft = FileTool()
    res = ft.replace_in_file(path, old_code, new_code)
    is_err = "Error" in res or "Rejected" in res or "not found" in res.lower()
    return {"status": "error" if is_err else "success", "result": res, "path": path}

# Register with default_registry
default_registry.register(ToolDefinition(
    name="file.read",
    description="Read complete content from a file.",
    category="fs",
    parameters={"path": "str"},
    permissions=[Permission.READ_FILE],
    callback=canonical_file_read
))

default_registry.register(ToolDefinition(
    name="file.write",
    description="Write content to a file with AST syntax validation for Python.",
    category="fs",
    parameters={"path": "str", "content": "str"},
    permissions=[Permission.WRITE_FILE],
    callback=canonical_file_write
))

default_registry.register(ToolDefinition(
    name="file.view_outline",
    description="View structural outline of a file (classes, methods, functions with line numbers).",
    category="fs",
    parameters={"path": "str"},
    permissions=[Permission.READ_FILE],
    callback=canonical_view_file_outline
))

default_registry.register(ToolDefinition(
    name="file.read_lines",
    description="Read specific line ranges with line numbers prefixed.",
    category="fs",
    parameters={"path": "str", "start_line": "int", "end_line": "int"},
    permissions=[Permission.READ_FILE],
    callback=canonical_read_file_lines
))

default_registry.register(ToolDefinition(
    name="file.replace",
    description="Surgically replace a block of code with syntax compile verification.",
    category="fs",
    parameters={"path": "str", "old_code": "str", "new_code": "str"},
    permissions=[Permission.WRITE_FILE],
    callback=canonical_replace_in_file
))


class FileTool:
    """
    Advanced surgical file manipulation suite with built-in AST verification.
    """
    agent: Any = None

    def __init__(self, agent: Any = None):
        self.agent = agent

    def read(self, path: str) -> str:
        try:
            path = enforce_boundary(path)
            if not os.path.exists(path):
                return f"Error: File not found: {path}"
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def view_file_outline(self, path: str) -> str:
        """
        Parses code structure and returns classes, methods, and functions with exact line ranges.
        For Python files, uses AST. For other files, uses pattern matching.
        """
        try:
            path = enforce_boundary(path)
            if not os.path.exists(path):
                return f"Error: File not found: {path}"

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.splitlines()
            total_lines = len(lines)

            if path.endswith(".py"):
                try:
                    tree = ast.parse(content, filename=path)
                    outline = [f"Outline of {path} ({total_lines} lines total):"]
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            end = getattr(node, 'end_lineno', node.lineno)
                            outline.append(f"  L{node.lineno}-L{end}: class {node.name}")
                            for item in node.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    m_end = getattr(item, 'end_lineno', item.lineno)
                                    args = [a.arg for a in item.args.args]
                                    prefix = "async def" if isinstance(item, ast.AsyncFunctionDef) else "def"
                                    outline.append(f"    L{item.lineno}-L{m_end}: {prefix} {item.name}({', '.join(args)})")
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            end = getattr(node, 'end_lineno', node.lineno)
                            args = [a.arg for a in node.args.args]
                            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                            outline.append(f"  L{node.lineno}-L{end}: {prefix} {node.name}({', '.join(args)})")
                        elif isinstance(node, ast.Assign):
                            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                            if targets:
                                outline.append(f"  L{node.lineno}: {', '.join(targets)} = ...")
                    return "\n".join(outline) if len(outline) > 1 else f"Outline of {path}: No top-level classes or functions detected ({total_lines} lines)."
                except SyntaxError as e:
                    return f"Warning: SyntaxError on line {e.lineno} while parsing AST outline of {path}. Reading line count: {total_lines} lines."

            # Non-python fallback (JS/TS/Rust/Go/Dart/MD)
            outline = [f"Outline of {path} ({total_lines} lines total):"]
            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if re.match(r'^(?:export\s+)?(?:class|function|async\s+function|interface|type|struct|enum)\b', stripped) or \
                   re.match(r'^(?:def|fn|func|pub\s+fn)\b', stripped) or \
                   (path.endswith('.md') and stripped.startswith('#')):
                    outline.append(f"  L{idx}: {stripped[:90]}")
            return "\n".join(outline) if len(outline) > 1 else f"Outline of {path}: ({total_lines} lines)."
        except Exception as e:
            return f"Error generating outline: {str(e)}"

    def read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        """
        Reads a specific slice of lines with 1-indexed line numbers prefixed.
        """
        try:
            path = enforce_boundary(path)
            if not os.path.exists(path):
                return f"Error: File not found: {path}"

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total = len(lines)
            start = max(1, int(start_line))
            end = min(total, int(end_line))

            if start > total:
                return f"Error: start_line {start} exceeds total lines in file ({total})."
            if start > end:
                return f"Error: start_line {start} cannot be greater than end_line {end}."

            output = [f"=== {path} (Lines {start}-{end} of {total}) ==="]
            for i in range(start - 1, end):
                output.append(f"{i + 1:5d} | {lines[i].rstrip()}")
            return "\n".join(output)
        except Exception as e:
            return f"Error reading lines from {path}: {str(e)}"

    def replace_in_file(self, path: str, old_code: str, new_code: str) -> str:
        """
        Surgically replaces a block of code with built-in AST compile validation.
        Prevents corrupting files with indentation or syntax errors.
        """
        try:
            path = enforce_boundary(path)
        except Exception as e:
            return f"Error: {str(e)}"

        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_code in content:
                new_content = content.replace(old_code, new_code, 1)
            else:
                # Codex-grade fuzzy line matching fallback
                from lmms.backend.tools.patch import seek_sequence
                content_lines = content.splitlines()
                pattern_lines = old_code.splitlines()
                match_idx = seek_sequence(content_lines, pattern_lines, start=0)
                if match_idx is not None:
                    new_lines = list(content_lines)
                    new_lines[match_idx : match_idx + len(pattern_lines)] = new_code.splitlines()
                    new_content = "\n".join(new_lines)
                    if content.endswith("\n") and not new_content.endswith("\n"):
                        new_content += "\n"
                else:
                    return f"Error: Target code block not found in {path}. Make sure the code to replace matches exactly."

            # Built-in AST Syntax Guard for Python
            if path.endswith(".py"):
                try:
                    ast.parse(new_content, filename=path)
                except SyntaxError as e:
                    return (
                        f"REJECTED: Proposed modification creates SyntaxError on line {e.lineno}: {e.msg}\n"
                        f"Problematic code: {e.text}\n"
                        f"File was NOT modified. Please fix syntax or indentation and retry."
                    )

            # Record pre-modification state for non-destructive /undo
            _record_pre_state(path)

            # Write changes
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            diff = list(difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                n=3
            ))

            diff_str = "".join(diff[:40])
            if hasattr(self, "agent") and self.agent:
                self.agent.push_action({
                    "type": "file_replace",
                    "path": path,
                    "old_content": content,
                    "new_content": new_content
                })

            return f"Successfully modified {path}.\nDiff:\n{diff_str}"
        except Exception as e:
            return f"Error during replacement in {path}: {str(e)}"

    def write(self, path: str, content: str) -> str:
        try:
            path = enforce_boundary(path)
        except Exception as e:
            return f"Error: {str(e)}"

        old_content = None
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_content = f.read()
            except Exception:
                pass

        # AST syntax guard before saving python files
        if path.endswith(".py"):
            try:
                ast.parse(content, filename=path)
            except SyntaxError as e:
                return (
                    f"REJECTED: Writing to {path} cancelled due to SyntaxError on line {e.lineno}: {e.msg}\n"
                    f"File was NOT modified. Please ensure proper Python syntax before writing."
                )

        _record_pre_state(path)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            if hasattr(self, "agent") and self.agent:
                self.agent.push_action({
                    "type": "file_write",
                    "path": path,
                    "old_content": old_content,
                    "new_content": content
                })
            
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def edit_in_vscode(self, path: str) -> str:
        try:
            subprocess.Popen(["code", path])
            return f"Opened {path} in VS Code."
        except Exception as e:
            return f"Failed to open in VS Code: {str(e)}"

    def list_folder(self, path: str = ".") -> str:
        try:
            enforce_boundary(path)
            if not os.path.exists(path):
                return f"Path {path} does not exist."

            result = []
            for root, dirs, files in os.walk(path):
                # Skip heavy/cache directories
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.pytest_cache', 'node_modules', 'venv', '.venv')]
                level = root.replace(path, "").count(os.sep)
                indent = " " * 4 * level
                result.append(f"{indent}{os.path.basename(root)}/")
                subindent = " " * 4 * (level + 1)
                for f in files:
                    result.append(f"{subindent}{f}")

                if len(result) > 250:
                    result.append(f"{subindent}... (truncated at 250 items)")
                    break
            return "\n".join(result)
        except Exception as e:
            return f"Error listing folder: {str(e)}"

    def create_folder(self, path: str) -> str:
        try:
            enforce_boundary(path)
            os.makedirs(path, exist_ok=True)
            return f"Created folder {path}"
        except Exception as e:
            return f"Error creating folder: {str(e)}"

    def delete(self, path: str, confirm: bool = False) -> str:
        try:
            enforce_boundary(path)
        except Exception as e:
            return f"Error: {str(e)}"

        if not confirm:
            return f"Delete operation requires confirm=True to execute. Path: {path}"

        _record_pre_state(path)
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                return f"Path {path} not found."
            return f"Deleted {path}"
        except Exception as e:
            return f"Error deleting: {str(e)}"

    def search_in_files(self, folder: str = ".", query: str = "") -> str:
        try:
            enforce_boundary(folder)
            results = []
            for root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.pytest_cache', 'node_modules')]
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                if query in line:
                                    results.append(f"{filepath}:{i+1}: {line.strip()}")
                                    if len(results) > 60:
                                        results.append("... (truncated at 60 matches)")
                                        return "\n".join(results)
                    except Exception:
                        pass
            if not results:
                return "No matches found."
            return "\n".join(results)
        except Exception as e:
            return f"Error searching files: {str(e)}"


# Module-level convenience functions matching FileTool methods
_default_file_tool = FileTool()

def read(path: str) -> str:
    return _default_file_tool.read(path)

def write(path: str, content: str) -> str:
    return _default_file_tool.write(path, content)

def view_file_outline(path: str) -> str:
    return _default_file_tool.view_file_outline(path)

def read_file_lines(path: str, start_line: int, end_line: int) -> str:
    return _default_file_tool.read_file_lines(path, start_line, end_line)

def replace_in_file(path: str, old_code: str, new_code: str) -> str:
    return _default_file_tool.replace_in_file(path, old_code, new_code)

def list_folder(path: str = ".") -> str:
    return _default_file_tool.list_folder(path)

def search_in_files(folder: str = ".", query: str = "") -> str:
    return _default_file_tool.search_in_files(folder, query)

__all__ = [
    "FileTool",
    "read",
    "write",
    "view_file_outline",
    "read_file_lines",
    "replace_in_file",
    "list_folder",
    "search_in_files",
    "canonical_file_read",
    "canonical_file_write",
    "canonical_view_file_outline",
    "canonical_read_file_lines",
    "canonical_replace_in_file",
]

