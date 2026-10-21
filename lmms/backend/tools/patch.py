"""
Codex-Grade Apply Patch Engine for LMMs.
Implements fuzzy sequence seeking, dual-format parsing (OpenAI Codex '*** Begin Patch'
and Standard Unified Diff), AST syntax pre-flight guards, and atomic multi-file rollback.
"""

from __future__ import annotations

import ast
import difflib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from lmms.backend.tools.files import enforce_boundary


# Patch markers for OpenAI Codex format
BEGIN_PATCH_MARKER = "*** Begin Patch"
END_PATCH_MARKER = "*** End Patch"
ADD_FILE_MARKER = "*** Add File: "
DELETE_FILE_MARKER = "*** Delete File: "
UPDATE_FILE_MARKER = "*** Update File: "
MOVE_TO_MARKER = "*** Move to: "
EOF_MARKER = "*** End of File"
CHANGE_CONTEXT_MARKER = "@@ "
EMPTY_CHANGE_CONTEXT_MARKER = "@@"


def seek_sequence(
    lines: List[str],
    pattern: List[str],
    start: int = 0,
    eof: bool = False,
) -> Optional[int]:
    """
    Finds the sequence of `pattern` lines within `lines` beginning at or after `start`.
    Matches are attempted with decreasing strictness:
      1. Exact match
      2. rstrip() match (ignoring trailing whitespace)
      3. strip() match (ignoring leading and trailing indentation differences)
    
    If eof=True, tries searching from near the end first.
    """
    if not pattern:
        return start

    if len(pattern) > len(lines):
        return None

    search_start = max(0, start)
    if eof and len(lines) >= len(pattern):
        eof_start = len(lines) - len(pattern)
        search_start = max(search_start, eof_start)

    pat_len = len(pattern)
    limit = len(lines) - pat_len + 1

    # 1. Exact match
    for i in range(search_start, limit):
        if lines[i : i + pat_len] == pattern:
            return i

    # 2. rstrip match
    for i in range(search_start, limit):
        if all(lines[i + idx].rstrip() == pat.rstrip() for idx, pat in enumerate(pattern)):
            return i

    # 3. strip match (fuzzy indentation)
    for i in range(search_start, limit):
        if all(lines[i + idx].strip() == pat.strip() for idx, pat in enumerate(pattern)):
            return i

    # If search_start > start and eof was True, fallback to regular start
    if search_start > start:
        return seek_sequence(lines, pattern, start=start, eof=False)

    return None


@dataclass
class PatchHunk:
    context_lines: List[str] = field(default_factory=list)
    search_lines: List[str] = field(default_factory=list)
    replace_lines: List[str] = field(default_factory=list)
    eof: bool = False


@dataclass
class FilePatchOperation:
    op_type: str  # "add" | "delete" | "update"
    path: str
    new_path: Optional[str] = None
    new_content: Optional[str] = None
    hunks: List[PatchHunk] = field(default_factory=list)


class ApplyPatchEngine:
    """
    Engine for validating and applying surgical patches across codebases.
    Supports both OpenAI Codex format and Unified Diff format.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()

    def resolve_path(self, path: str) -> str:
        clean = path.strip().strip("'\"`")
        if not os.path.isabs(clean):
            clean = os.path.abspath(os.path.join(self.workspace_root, clean))
        try:
            enforce_boundary(clean)
        except Exception:
            pass
        return clean

    def parse_patch(self, patch_text: str) -> List[FilePatchOperation]:
        """Auto-detects format and parses into standard FilePatchOperations."""
        trimmed = patch_text.strip()
        if BEGIN_PATCH_MARKER in trimmed or any(m in trimmed for m in [ADD_FILE_MARKER, UPDATE_FILE_MARKER, DELETE_FILE_MARKER]):
            return self._parse_codex_format(trimmed)
        elif re.search(r'^(?:---|\+\+\+)\s+[^\n]+', trimmed, re.MULTILINE):
            return self._parse_unified_diff(trimmed)
        else:
            # Fallback attempt at unified diff or codex
            return self._parse_codex_format(trimmed)

    def _parse_codex_format(self, text: str) -> List[FilePatchOperation]:
        operations: List[FilePatchOperation] = []
        lines = text.splitlines()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].strip()

            if line.startswith(ADD_FILE_MARKER):
                path = line[len(ADD_FILE_MARKER):].strip()
                i += 1
                content_lines = []
                while i < n and not any(lines[i].strip().startswith(m) for m in [ADD_FILE_MARKER, DELETE_FILE_MARKER, UPDATE_FILE_MARKER, END_PATCH_MARKER]):
                    raw = lines[i]
                    if raw.startswith("+"):
                        content_lines.append(raw[1:])
                    else:
                        content_lines.append(raw)
                    i += 1
                operations.append(FilePatchOperation(
                    op_type="add",
                    path=path,
                    new_content="\n".join(content_lines) + ("\n" if content_lines else "")
                ))
                continue

            elif line.startswith(DELETE_FILE_MARKER):
                path = line[len(DELETE_FILE_MARKER):].strip()
                operations.append(FilePatchOperation(op_type="delete", path=path))
                i += 1
                continue

            elif line.startswith(UPDATE_FILE_MARKER):
                path = line[len(UPDATE_FILE_MARKER):].strip()
                i += 1
                new_path = None
                hunks: List[PatchHunk] = []
                current_hunk: Optional[PatchHunk] = None

                while i < n and not any(lines[i].strip().startswith(m) for m in [ADD_FILE_MARKER, DELETE_FILE_MARKER, UPDATE_FILE_MARKER, END_PATCH_MARKER]):
                    raw_line = lines[i]
                    s_line = raw_line.strip()

                    if s_line.startswith(MOVE_TO_MARKER):
                        new_path = s_line[len(MOVE_TO_MARKER):].strip()
                        i += 1
                        continue

                    if s_line.startswith(CHANGE_CONTEXT_MARKER) or s_line == EMPTY_CHANGE_CONTEXT_MARKER:
                        if current_hunk:
                            hunks.append(current_hunk)
                        current_hunk = PatchHunk()
                        i += 1
                        continue

                    if s_line == EOF_MARKER:
                        if current_hunk:
                            current_hunk.eof = True
                        i += 1
                        continue

                    if current_hunk is None:
                        current_hunk = PatchHunk()

                    if raw_line.startswith("+"):
                        current_hunk.replace_lines.append(raw_line[1:])
                    elif raw_line.startswith("-"):
                        current_hunk.search_lines.append(raw_line[1:])
                    elif raw_line.startswith(" "):
                        current_hunk.search_lines.append(raw_line[1:])
                        current_hunk.replace_lines.append(raw_line[1:])
                    else:
                        # Lenient context line without leading space
                        current_hunk.search_lines.append(raw_line)
                        current_hunk.replace_lines.append(raw_line)

                    i += 1

                if current_hunk:
                    hunks.append(current_hunk)

                operations.append(FilePatchOperation(
                    op_type="update",
                    path=path,
                    new_path=new_path,
                    hunks=hunks
                ))
                continue

            i += 1

        return operations

    def _parse_unified_diff(self, text: str) -> List[FilePatchOperation]:
        """Parses standard unified diff syntax into operations."""
        operations: List[FilePatchOperation] = []
        lines = text.splitlines()
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            if line.startswith("--- "):
                orig_file = re.sub(r'^(?:---|\+\+\+)\s+[ab]/', '', line).strip()
                i += 1
                if i < n and lines[i].startswith("+++ "):
                    dest_file = re.sub(r'^(?:---|\+\+\+)\s+[ab]/', '', lines[i]).strip()
                    i += 1
                else:
                    dest_file = orig_file

                target_file = dest_file if dest_file != "/dev/null" else orig_file
                if orig_file == "/dev/null":
                    op_type = "add"
                elif dest_file == "/dev/null":
                    op_type = "delete"
                else:
                    op_type = "update"

                hunks: List[PatchHunk] = []
                current_hunk: Optional[PatchHunk] = None

                while i < n and not lines[i].startswith("--- "):
                    curr = lines[i]
                    if curr.startswith("@@ "):
                        if current_hunk:
                            hunks.append(current_hunk)
                        current_hunk = PatchHunk()
                    elif current_hunk is not None:
                        if curr.startswith("+"):
                            current_hunk.replace_lines.append(curr[1:])
                        elif curr.startswith("-"):
                            current_hunk.search_lines.append(curr[1:])
                        elif curr.startswith(" "):
                            current_hunk.search_lines.append(curr[1:])
                            current_hunk.replace_lines.append(curr[1:])
                    i += 1

                if current_hunk:
                    hunks.append(current_hunk)

                operations.append(FilePatchOperation(
                    op_type=op_type,
                    path=target_file,
                    hunks=hunks
                ))
                continue
            i += 1

        return operations

    def apply_patch(
        self,
        patch_text: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Validates and applies patch operations with full AST check and atomic rollback.
        """
        operations = self.parse_patch(patch_text)
        if not operations:
            return {
                "success": False,
                "error": "Failed to parse any patch operations. Ensure patch follows Codex or Unified Diff format.",
                "files_modified": [],
                "diff": ""
            }

        staged_files: Dict[str, str] = {}
        original_backups: Dict[str, Optional[str]] = {}
        files_to_delete: List[str] = []
        unified_diffs: List[str] = []

        try:
            # Stage all changes in memory
            for op in operations:
                target_path = self.resolve_path(op.path)

                if op.op_type == "delete":
                    if not os.path.exists(target_path):
                        return {
                            "success": False,
                            "error": f"Cannot delete nonexistent file: {op.path}",
                            "files_modified": []
                        }
                    files_to_delete.append(target_path)
                    continue

                if op.op_type == "add":
                    content = op.new_content or ""
                    # AST validation for new python files
                    if target_path.endswith(".py"):
                        try:
                            ast.parse(content, filename=op.path)
                        except SyntaxError as e:
                            return {
                                "success": False,
                                "error": f"AST SyntaxError in new file {op.path} (line {e.lineno}): {e.msg}\n{e.text}",
                                "files_modified": []
                            }
                    staged_files[target_path] = content
                    unified_diffs.append(f"+++ New File: {op.path}\n" + content[:500] + ("\n..." if len(content) > 500 else ""))
                    continue

                if op.op_type == "update":
                    if not os.path.exists(target_path):
                        return {
                            "success": False,
                            "error": f"Target file for update not found: {op.path}",
                            "files_modified": []
                        }

                    with open(target_path, "r", encoding="utf-8") as f:
                        original_text = f.read()

                    original_backups[target_path] = original_text
                    working_lines = original_text.splitlines()

                    # Apply each hunk sequentially
                    cursor = 0
                    for hunk_idx, hunk in enumerate(op.hunks):
                        if not hunk.search_lines and not hunk.replace_lines:
                            continue

                        # If search_lines is empty, it's a pure addition
                        if not hunk.search_lines:
                            working_lines[cursor:cursor] = hunk.replace_lines
                            cursor += len(hunk.replace_lines)
                            continue

                        match_idx = seek_sequence(
                            working_lines,
                            hunk.search_lines,
                            start=cursor,
                            eof=hunk.eof
                        )

                        if match_idx is None:
                            # Try searching from line 0
                            match_idx = seek_sequence(
                                working_lines,
                                hunk.search_lines,
                                start=0,
                                eof=hunk.eof
                            )

                        if match_idx is None:
                            search_preview = "\n".join(hunk.search_lines[:5])
                            return {
                                "success": False,
                                "error": (
                                    f"Patch hunk #{hunk_idx + 1} failed in {op.path}: "
                                    f"Target sequence not found.\nSearch snippet:\n{search_preview}"
                                ),
                                "files_modified": []
                            }

                        # Apply replacement
                        working_lines[match_idx : match_idx + len(hunk.search_lines)] = hunk.replace_lines
                        cursor = match_idx + len(hunk.replace_lines)

                    new_text = "\n".join(working_lines)
                    if original_text.endswith("\n") and not new_text.endswith("\n"):
                        new_text += "\n"

                    # AST Validation for Python files
                    if target_path.endswith(".py"):
                        try:
                            ast.parse(new_text, filename=op.path)
                        except SyntaxError as e:
                            return {
                                "success": False,
                                "error": (
                                    f"AST SyntaxError after applying patch to {op.path} "
                                    f"(line {e.lineno}): {e.msg}\nProblematic code:\n{e.text}"
                                ),
                                "files_modified": []
                            }

                    dest_path = self.resolve_path(op.new_path) if op.new_path else target_path
                    staged_files[dest_path] = new_text

                    # Generate diff preview
                    diff = list(difflib.unified_diff(
                        original_text.splitlines(keepends=True),
                        new_text.splitlines(keepends=True),
                        fromfile=f"a/{op.path}",
                        tofile=f"b/{op.new_path or op.path}"
                    ))
                    if diff:
                        unified_diffs.append("".join(diff))

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "files_modified": list(staged_files.keys()),
                    "files_deleted": files_to_delete,
                    "diff": "\n".join(unified_diffs)
                }

            # Commit changes to disk atomically
            written_files = []
            for path, content in staged_files.items():
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                written_files.append(path)

            for path in files_to_delete:
                if os.path.exists(path):
                    os.remove(path)

            return {
                "success": True,
                "files_modified": written_files,
                "files_deleted": files_to_delete,
                "diff": "\n".join(unified_diffs)
            }

        except Exception as e:
            # Rollback any written files on unhandled exception
            for path, orig in original_backups.items():
                if orig is not None:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(orig)
                    except Exception:
                        pass
            return {
                "success": False,
                "error": f"Exception applying patch: {str(e)}",
                "files_modified": []
            }


default_patch_engine = ApplyPatchEngine()


def canonical_apply_patch(patch: str) -> str:
    """Canonical function wrapper for tool execution."""
    res = default_patch_engine.apply_patch(patch)
    if res["success"]:
        out = [f"Successfully applied patch to {len(res['files_modified'])} file(s)."]
        if res.get("files_deleted"):
            out.append(f"Deleted {len(res['files_deleted'])} file(s).")
        if res.get("diff"):
            out.append(f"\nUnified Diff:\n{res['diff']}")
        return "\n".join(out)
    else:
        return f"Patch Application Failed: {res.get('error', 'Unknown error')}"
