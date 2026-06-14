import os
import json
from typing import Dict, Any, List

class AgentRegistry:
    """
    Loads and tracks Agent Manifests.
    """
    def __init__(self, manifests_dir: str):
        self.manifests_dir = manifests_dir
        self.manifests: Dict[str, Dict[str, Any]] = {}
        self.load_manifests()

    def load_manifests(self):
        if not os.path.exists(self.manifests_dir):
            return
        
        for file in os.listdir(self.manifests_dir):
            if file.endswith(".json"):
                with open(os.path.join(self.manifests_dir, file), "r") as f:
                    try:
                        data = json.load(f)
                        if "name" in data:
                            self.manifests[data["name"]] = data
                    except Exception as e:
                        print(f"Failed to load manifest {file}: {e}")

    def get_manifest(self, agent_name: str) -> Dict[str, Any]:
        return self.manifests.get(agent_name, {})

    def list_agents(self) -> List[Dict[str, Any]]:
        return list(self.manifests.values())
