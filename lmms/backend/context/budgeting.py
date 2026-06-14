from lmms.backend.context.capabilities import TokenBudget

class BudgetEngine:
    def __init__(self):
        # Stubbed runtime profiles. These would be loaded from disk or DB.
        self.profiles = {
            "default_4k": {
                "max_tokens": 4096,
                "allocations": {
                    "system": 0.10,
                    "workspace": 0.10,
                    "tasks": 0.15,
                    "git": 0.15,
                    "memory": 0.25,
                    "files": 0.15,
                    "tools": 0.10
                }
            },
            "default_32k": {
                "max_tokens": 32768,
                "allocations": {
                    "system": 0.05,
                    "workspace": 0.10,
                    "tasks": 0.10,
                    "git": 0.10,
                    "memory": 0.30,
                    "files": 0.25,
                    "tools": 0.10
                }
            }
        }

    def allocate(self, profile_name: str) -> TokenBudget:
        profile = self.profiles.get(profile_name, self.profiles["default_4k"])
        max_t = profile["max_tokens"]
        alloc = profile["allocations"]
        
        return TokenBudget(
            max_tokens=max_t,
            system_tokens=int(max_t * alloc["system"]),
            workspace_tokens=int(max_t * alloc["workspace"]),
            task_tokens=int(max_t * alloc["tasks"]),
            git_tokens=int(max_t * alloc["git"]),
            memory_tokens=int(max_t * alloc["memory"]),
            file_tokens=int(max_t * alloc["files"]),
            tool_tokens=int(max_t * alloc["tools"])
        )
