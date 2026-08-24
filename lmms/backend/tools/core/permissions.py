from enum import Enum
from typing import List, Set

class Permission(Enum):
    READ_ONLY = "READ_ONLY"
    SAFE_WRITE = "SAFE_WRITE"
    NETWORK = "NETWORK"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    GIT_MUTATION = "GIT_MUTATION"
    DESTRUCTIVE = "DESTRUCTIVE"

class ToolPermissionManager:
    """
    Manages and enforces tool execution permissions.
    """
    def __init__(self, granted_permissions: List[Permission] = None):
        if granted_permissions is None:
            # By default, assume a safe profile
            self.granted_permissions: Set[Permission] = {
                Permission.READ_ONLY, 
                Permission.SAFE_WRITE, 
                Permission.NETWORK
            }
        else:
            self.granted_permissions = set(granted_permissions)
            
    def grant(self, permission: Permission):
        self.granted_permissions.add(permission)
        
    def revoke(self, permission: Permission):
        self.granted_permissions.discard(permission)

    def check_permission(self, required_permissions: List[Permission]) -> bool:
        for p in required_permissions:
            if p not in self.granted_permissions:
                return False
        return True
