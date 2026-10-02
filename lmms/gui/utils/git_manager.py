import git
from PyQt6.QtCore import QObject, pyqtSignal
import os

class GitManager(QObject):
    repo_changed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, repo_path, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            self.repo = None
            
    def init_repo(self):
        try:
            self.repo = git.Repo.init(self.repo_path)
            self.repo_changed.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def is_valid(self):
        return self.repo is not None

    def get_status(self):
        if not self.is_valid():
            return {"untracked": [], "modified": [], "staged": []}
            
        try:
            untracked = self.repo.untracked_files
            changed = [item.a_path for item in self.repo.index.diff(None)]
            staged = [item.a_path for item in self.repo.index.diff("HEAD")] if self.repo.head.is_valid() else [item[0] for item in self.repo.index.entries.keys()]
            
            return {
                "untracked": untracked,
                "modified": changed,
                "staged": staged
            }
        except Exception as e:
            self.error_occurred.emit(str(e))
            return {"untracked": [], "modified": [], "staged": []}

    def get_diff(self, file_path):
        if not self.is_valid():
            return ""
        try:
            diffs = self.repo.index.diff(None, paths=[file_path], create_patch=True)
            if diffs:
                return diffs[0].diff.decode('utf-8')
            return ""
        except Exception as e:
            self.error_occurred.emit(str(e))
            return ""

    def compute_decorations(self, file_path, current_content):
        if not self.is_valid():
            return []
            
        try:
            # Get the relative path for git
            rel_path = os.path.relpath(file_path, self.repo_path)
            # Fetch the old content from the index (or HEAD if index is empty)
            try:
                old_content = self.repo.git.show(f":{rel_path}")
            except Exception:
                # Untracked file -> all added
                lines = current_content.splitlines()
                if not lines: return []
                return [{"type": "added", "start": 1, "end": len(lines)}]
                
            import difflib
            sm = difflib.SequenceMatcher(None, old_content.splitlines(), current_content.splitlines())
            changes = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'replace':
                    changes.append({"type": "modified", "start": j1+1, "end": j2})
                elif tag == 'delete':
                    changes.append({"type": "deleted", "start": j1+1})
                elif tag == 'insert':
                    changes.append({"type": "added", "start": j1+1, "end": j2})
            return changes
        except Exception as e:
            print("Decorations error:", e)
            return []

    def get_blame(self, file_path):
        """Returns line-by-line blame info."""
        if not self.is_valid():
            return {}
        try:
            import time
            import datetime
            rel_path = os.path.relpath(file_path, self.repo_path)
            blame_out = self.repo.git.blame(rel_path, "--line-porcelain")
            
            blame_data = {}
            current_commit = None
            current_line = None
            
            commits = {} # hash -> info
            
            for line in blame_out.splitlines():
                if not line:
                    continue
                if not current_commit:
                    parts = line.split(" ")
                    current_commit = parts[0]
                    # original line, final line, group lines
                    current_line = int(parts[2])
                    if current_commit not in commits:
                        commits[current_commit] = {"hash": current_commit}
                elif line.startswith("author "):
                    commits[current_commit]["author"] = line[7:]
                elif line.startswith("author-time "):
                    timestamp = int(line[12:])
                    # convert to relative time
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    now = datetime.datetime.now()
                    diff = now - dt
                    if diff.days > 365:
                        commits[current_commit]["time"] = f"{diff.days // 365} years ago"
                    elif diff.days > 30:
                        commits[current_commit]["time"] = f"{diff.days // 30} months ago"
                    elif diff.days > 0:
                        commits[current_commit]["time"] = f"{diff.days} days ago"
                    else:
                        commits[current_commit]["time"] = "today"
                elif line.startswith("summary "):
                    commits[current_commit]["summary"] = line[8:]
                elif line.startswith("\t"): # file content line
                    blame_data[current_line] = commits[current_commit]
                    current_commit = None
                    current_line = None
            
            # Now we only want to return strings for each line to display in the editor
            # E.g. {1: "markanm, 3 days ago • Initial commit", ...}
            # Or if it's the 000000 commit (uncommitted), return "Not Committed Yet"
            result = {}
            for line_no, info in blame_data.items():
                if info["hash"].startswith("000000"):
                    result[line_no] = "Not Committed Yet"
                else:
                    result[line_no] = f"{info.get('author', 'Unknown')}, {info.get('time', '')} • {info.get('summary', '')}"
            return result
        except Exception as e:
            return {}

    def stage_file(self, file_path):
        if not self.is_valid(): return
        try:
            self.repo.index.add([file_path])
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def unstage_file(self, file_path):
        if not self.is_valid(): return
        try:
            if self.repo.head.is_valid():
                self.repo.index.reset(commit="HEAD", paths=[file_path])
            else:
                # If there are no commits yet, we rm it from index
                self.repo.index.remove([file_path], cached=True)
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def commit(self, message):
        if not self.is_valid(): return
        try:
            self.repo.index.commit(message)
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def push(self):
        if not self.is_valid(): return
        try:
            origin = self.repo.remotes.origin
            origin.push()
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def pull(self):
        if not self.is_valid(): return
        try:
            origin = self.repo.remotes.origin
            origin.pull()
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def get_current_branch(self):
        if not self.is_valid(): return "unknown"
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached head
            return "detached"
        except Exception:
            return "unknown"

    def get_branches(self):
        if not self.is_valid(): return []
        try:
            return [head.name for head in self.repo.heads]
        except Exception:
            return []

    def checkout_branch(self, branch_name):
        if not self.is_valid(): return
        try:
            self.repo.git.checkout(branch_name)
            self.repo_changed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
