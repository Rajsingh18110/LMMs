import keyring
from github import Github
from PyQt6.QtCore import QObject, pyqtSignal

SERVICE_NAME = "LMMsEditor_GitHub"

class GitHubManager(QObject):
    auth_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.github = None
        self.user = None
        self._load_token()
        
    def _load_token(self):
        token = keyring.get_password(SERVICE_NAME, "user")
        if token:
            self._init_github(token)
            
    def _init_github(self, token):
        try:
            self.github = Github(token)
            self.user = self.github.get_user()
            # Test auth
            _ = self.user.login
            self.auth_changed.emit(True)
        except Exception as e:
            self.github = None
            self.user = None
            keyring.delete_password(SERVICE_NAME, "user")
            self.error_occurred.emit(f"GitHub Auth failed: {e}")
            self.auth_changed.emit(False)
            
    def authenticate(self, token):
        try:
            keyring.set_password(SERVICE_NAME, "user", token)
            self._init_github(token)
            return self.is_authenticated()
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
            
    def is_authenticated(self):
        return self.github is not None and self.user is not None
        
    def get_username(self):
        return self.user.login if self.is_authenticated() else None
        
    def logout(self):
        self.github = None
        self.user = None
        try:
            keyring.delete_password(SERVICE_NAME, "user")
        except Exception:
            pass
        self.auth_changed.emit(False)
        
    def clone_repo(self, repo_full_name, local_dir):
        if not self.is_authenticated():
            self.error_occurred.emit("Not authenticated with GitHub.")
            return False
        try:
            repo = self.github.get_repo(repo_full_name)
            # Build authenticated HTTPS URL
            token = keyring.get_password(SERVICE_NAME, "user")
            username = self.user.login
            clone_url = f"https://{username}:{token}@github.com/{repo_full_name}.git"
            import git
            git.Repo.clone_from(clone_url, local_dir, progress=None)
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def push_to_github(self, git_repo, remote_name="origin"):
        """Push a local GitPython Repo using the stored PAT for HTTPS auth."""
        if not self.is_authenticated():
            self.error_occurred.emit("Not authenticated with GitHub.")
            return False
        try:
            token = keyring.get_password(SERVICE_NAME, "user")
            username = self.user.login
            remote = git_repo.remote(remote_name)
            # Inject credentials into the remote URL temporarily
            old_url = remote.url
            if old_url.startswith("https://"):
                import re
                # Strip existing credentials if any
                auth_url = re.sub(
                    r"https://([^@]+@)?",
                    f"https://{username}:{token}@",
                    old_url
                )
                with remote.config_writer as cw:
                    cw.set("url", auth_url)
                try:
                    remote.push()
                finally:
                    with remote.config_writer as cw:
                        cw.set("url", old_url)
            else:
                remote.push()
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
