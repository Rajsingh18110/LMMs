from enum import Enum
from typing import List

class Permission(Enum):
    READ_FILE = "ReadFile"
    WRITE_FILE = "WriteFile"
    TERMINAL = "Terminal"
    WEB_SEARCH = "WebSearch"
    GIT_COMMIT = "GitCommit"
    GIT_DIFF = "GitDiff"
    GIT_BRANCH = "GitBranch"
    IMAGE_READ = "ImageRead"
    TASK_CREATE = "TaskCreate"
    TASK_UPDATE = "TaskUpdate"

class PermissionError(Exception):
    pass

class PermissionValidator:
    def validate(self, tool_name: str, agent_permissions: List[str]):
        """
        Validates if the requested tool corresponds to an allowed permission.
        Throws PermissionError if violated, which leads to AgentFailed.
        """
        # Hardcoded map of tools to permissions for Phase I.
        # This can be made dynamic using tool registries later.
        tool_permission_map = {
            "write_to_file": Permission.WRITE_FILE.value,
            "read_file": Permission.READ_FILE.value,
            "view_file": Permission.READ_FILE.value,
            "git_commit": Permission.GIT_COMMIT.value,
            "run_command": Permission.TERMINAL.value,
            "search_web": Permission.WEB_SEARCH.value
        }

        required_perm = tool_permission_map.get(tool_name)
        if required_perm and required_perm not in agent_permissions:
            raise PermissionError(f"Agent lacks permission: {required_perm} for tool: {tool_name}")
