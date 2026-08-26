import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QLineEdit, QComboBox,
    QMessageBox, QSizePolicy, QFrame, QDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from lmms.gui.utils.git_manager import GitManager
from lmms.gui.utils.github_manager import GitHubManager


class SourceControlPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Source Control", parent)
        self.setObjectName("SourceControlDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.git_manager = None
        self.github_manager = GitHubManager()
        self.github_manager.auth_changed.connect(self._on_auth_changed)
        self.github_manager.error_occurred.connect(self.show_error)
        self.init_ui()

    # ─── UI setup ───────────────────────────────────────────────────────────────

    def init_ui(self):
        container = QWidget()
        container.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #cccccc; }
            QLabel  { color: #cccccc; }
            QComboBox {
                background-color: #3c3c3c; color: #cccccc;
                border: 1px solid #555; padding: 3px;
            }
            QTreeWidget {
                background-color: #252526; color: #cccccc;
                border: none;
            }
            QTreeWidget::item:hover { background: #2a2d2e; }
            QTreeWidget::item:selected { background: #094771; }
            QTextEdit {
                background-color: #3c3c3c; color: #cccccc;
                border: 1px solid #555; border-radius: 2px;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── GitHub account bar ────────────────────────────────────────────────
        gh_bar = QHBoxLayout()

        self.lbl_gh_user = QLabel("Not signed in to GitHub")
        self.lbl_gh_user.setStyleSheet("color: #8b949e; font-size: 11px;")
        gh_bar.addWidget(self.lbl_gh_user)
        gh_bar.addStretch()

        self.btn_gh_login = QPushButton("Sign In")
        self.btn_gh_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gh_login.setFixedHeight(22)
        self.btn_gh_login.setStyleSheet("""
            QPushButton { background-color: #238636; color: white; border-radius: 3px;
                          padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_gh_login.clicked.connect(self._on_gh_login_clicked)
        gh_bar.addWidget(self.btn_gh_login)

        self.btn_gh_logout = QPushButton("Sign Out")
        self.btn_gh_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gh_logout.setFixedHeight(22)
        self.btn_gh_logout.setStyleSheet("""
            QPushButton { background-color: #555; color: white; border-radius: 3px;
                          padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background-color: #777; }
        """)
        self.btn_gh_logout.clicked.connect(self._on_gh_logout)
        self.btn_gh_logout.hide()
        gh_bar.addWidget(self.btn_gh_logout)

        layout.addLayout(gh_bar)

        # ── Divider ───────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #3d3d3d;")
        layout.addWidget(divider)

        # ── Branch selector + Sync/Clone ─────────────────────────────────────
        top_bar = QHBoxLayout()
        self.branch_combo = QComboBox()
        self.branch_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.branch_combo.currentIndexChanged.connect(self.on_branch_changed)
        top_bar.addWidget(QLabel("⎇"))
        top_bar.addWidget(self.branch_combo)

        self.btn_sync = QPushButton("↕ Sync")
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.setFixedHeight(24)
        self.btn_sync.setStyleSheet("""
            QPushButton { background-color: #3c3c3c; color: #cccccc;
                          border: 1px solid #555; border-radius: 2px; padding: 2px 8px; }
            QPushButton:hover { background-color: #4c4c4c; }
        """)
        self.btn_sync.clicked.connect(self.on_sync)
        top_bar.addWidget(self.btn_sync)

        self.btn_clone = QPushButton("⤓ Clone")
        self.btn_clone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clone.setFixedHeight(24)
        self.btn_clone.setStyleSheet("""
            QPushButton { background-color: #0e639c; color: white;
                          border-radius: 2px; padding: 2px 8px; }
            QPushButton:hover { background-color: #1177bb; }
        """)
        self.btn_clone.clicked.connect(self.on_clone)
        top_bar.addWidget(self.btn_clone)
        layout.addLayout(top_bar)

        # ── Commit message + button ───────────────────────────────────────────
        self.commit_input = QTextEdit()
        self.commit_input.setPlaceholderText("Commit message (Ctrl+Enter to commit)...")
        self.commit_input.setMaximumHeight(72)
        layout.addWidget(self.commit_input)

        commit_row = QHBoxLayout()
        self.btn_stage_all = QPushButton("+ Stage All")
        self.btn_stage_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stage_all.setFixedHeight(26)
        self.btn_stage_all.setStyleSheet("""
            QPushButton { background-color: #3c3c3c; color: #cccccc;
                          border: 1px solid #555; border-radius: 2px; padding: 2px 8px; }
            QPushButton:hover { background-color: #4c4c4c; }
        """)
        self.btn_stage_all.clicked.connect(self.on_stage_all)
        commit_row.addWidget(self.btn_stage_all)

        self.btn_commit = QPushButton("✔ Commit")
        self.btn_commit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_commit.setFixedHeight(26)
        self.btn_commit.setStyleSheet("""
            QPushButton { background-color: #0e639c; color: white;
                          border-radius: 2px; padding: 2px 10px; font-weight: bold; }
            QPushButton:hover { background-color: #1177bb; }
        """)
        self.btn_commit.clicked.connect(self.on_commit)
        commit_row.addWidget(self.btn_commit)
        layout.addLayout(commit_row)

        # ── Changes tree ─────────────────────────────────────────────────────
        self.tree_changes = QTreeWidget()
        self.tree_changes.setHeaderHidden(True)
        self.tree_changes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_changes.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree_changes)

        # ── Status bar ───────────────────────────────────────────────────────
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(self.lbl_status)

        self.setWidget(container)
        self._on_auth_changed(self.github_manager.is_authenticated())

    # ─── Workspace wiring ────────────────────────────────────────────────────

    def set_workspace(self, workspace_path):
        self.git_manager = GitManager(workspace_path, self)
        self.git_manager.repo_changed.connect(self.refresh_status)
        self.git_manager.error_occurred.connect(self.show_error)
        self.refresh_status()

    # ─── GitHub auth ─────────────────────────────────────────────────────────

    def _on_auth_changed(self, authenticated):
        if authenticated:
            username = self.github_manager.get_username()
            self.lbl_gh_user.setText(f"● GitHub: {username}")
            self.lbl_gh_user.setStyleSheet("color: #2ea043; font-size: 11px;")
            self.btn_gh_login.hide()
            self.btn_gh_logout.show()
        else:
            self.lbl_gh_user.setText("Not signed in to GitHub")
            self.lbl_gh_user.setStyleSheet("color: #8b949e; font-size: 11px;")
            self.btn_gh_login.show()
            self.btn_gh_logout.hide()

    def _on_gh_login_clicked(self):
        from lmms.gui.dialogs.github_auth_dialog import GitHubAuthDialog
        dlg = GitHubAuthDialog(self.github_manager, self)
        dlg.exec()

    def _on_gh_logout(self):
        self.github_manager.logout()

    # ─── Git status refresh ───────────────────────────────────────────────────

    def refresh_status(self):
        if not self.git_manager or not self.git_manager.is_valid():
            self.tree_changes.clear()
            item = QTreeWidgetItem(["No Git repository found"])
            item.setForeground(0, Qt.GlobalColor.gray)
            self.tree_changes.addTopLevelItem(item)
            return

        status = self.git_manager.get_status()
        self.tree_changes.clear()

        # Staged
        staged = status.get("staged", [])
        staged_parent = QTreeWidgetItem([f"Staged Changes ({len(staged)})"])
        staged_parent.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
        for f in staged:
            child = QTreeWidgetItem([f"  ✚  {f}"])
            child.setForeground(0, Qt.GlobalColor.green)
            child.setData(0, Qt.ItemDataRole.UserRole, ("staged", f))
            staged_parent.addChild(child)
        self.tree_changes.addTopLevelItem(staged_parent)

        # Changes + untracked
        changes = status.get("modified", []) + status.get("untracked", [])
        changes_parent = QTreeWidgetItem([f"Changes ({len(changes)})"])
        changes_parent.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
        for f in changes:
            child = QTreeWidgetItem([f"  M  {f}"])
            child.setForeground(0, Qt.GlobalColor.yellow)
            child.setData(0, Qt.ItemDataRole.UserRole, ("unstaged", f))
            changes_parent.addChild(child)
        self.tree_changes.addTopLevelItem(changes_parent)

        self.tree_changes.expandAll()

        # Branches
        self.branch_combo.blockSignals(True)
        self.branch_combo.clear()
        branches = self.git_manager.get_branches()
        current = self.git_manager.get_current_branch()
        self.branch_combo.addItems(branches)
        if current in branches:
            self.branch_combo.setCurrentText(current)
        self.branch_combo.blockSignals(False)

        total_changes = len(staged) + len(changes)
        self.lbl_status.setText(f"{total_changes} change(s) · branch: {current}")

    # ─── Actions ─────────────────────────────────────────────────────────────

    def on_stage_all(self):
        if not self.git_manager:
            return
        status = self.git_manager.get_status()
        all_files = status.get("modified", []) + status.get("untracked", [])
        for f in all_files:
            self.git_manager.stage_file(f)
        self.refresh_status()

    def on_commit(self):
        if not self.git_manager:
            return
        msg = self.commit_input.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "Git", "Commit message cannot be empty.")
            return
        self.git_manager.commit(msg)
        self.commit_input.clear()
        self.refresh_status()

    def on_sync(self):
        if not self.git_manager:
            return
        self.lbl_status.setText("Pulling…")
        self.git_manager.pull()
        self.lbl_status.setText("Pushing…")
        # Use PAT-authenticated push if signed in to GitHub
        if self.github_manager.is_authenticated() and self.git_manager.is_valid():
            self.github_manager.push_to_github(self.git_manager.repo)
        else:
            self.git_manager.push()
        self.lbl_status.setText("Sync complete.")
        self.refresh_status()

    def on_clone(self):
        """Clone a GitHub repo into a local directory."""
        if not self.github_manager.is_authenticated():
            QMessageBox.information(
                self, "GitHub",
                "Please sign in to GitHub first before cloning."
            )
            return

        repo_name, ok = QInputDialog.getText(
            self, "Clone Repository",
            "Enter repository (owner/repo):"
        )
        if not ok or not repo_name.strip():
            return

        local_dir, ok = QInputDialog.getText(
            self, "Clone Repository",
            "Enter local destination path:"
        )
        if not ok or not local_dir.strip():
            return

        self.lbl_status.setText(f"Cloning {repo_name}…")
        success = self.github_manager.clone_repo(repo_name.strip(), local_dir.strip())
        if success:
            QMessageBox.information(
                self, "Clone Complete",
                f"Repository cloned to:\n{local_dir}"
            )
            self.set_workspace(local_dir.strip())
        else:
            self.lbl_status.setText("Clone failed.")

    def on_branch_changed(self, _index):
        if not self.git_manager:
            return
        branch = self.branch_combo.currentText()
        if branch:
            self.git_manager.checkout_branch(branch)

    # ─── Context menu ─────────────────────────────────────────────────────────

    def show_context_menu(self, position):
        if not self.git_manager:
            return
        item = self.tree_changes.itemAt(position)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        state, file_path = data
        from PyQt6.QtWidgets import QMenu
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #252526; color: #cccccc;
                    border: 1px solid #454545; }
            QMenu::item:selected { background-color: #094771; }
        """)

        if state == "unstaged":
            action_stage = menu.addAction("Stage Changes")
            action_discard = menu.addAction("Discard Changes")
            res = menu.exec(self.tree_changes.viewport().mapToGlobal(position))
            if res == action_stage:
                self.git_manager.stage_file(file_path)
                self.refresh_status()
            elif res == action_discard:
                self._discard_changes(file_path)
        elif state == "staged":
            action_unstage = menu.addAction("Unstage Changes")
            res = menu.exec(self.tree_changes.viewport().mapToGlobal(position))
            if res == action_unstage:
                self.git_manager.unstage_file(file_path)
                self.refresh_status()

    def _discard_changes(self, file_path):
        reply = QMessageBox.question(
            self, "Discard Changes",
            f"Are you sure you want to discard changes to:\n{file_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.git_manager.repo.git.checkout("--", file_path)
                self.refresh_status()
            except Exception as e:
                self.show_error(str(e))

    # ─── Error display ────────────────────────────────────────────────────────

    def show_error(self, err):
        if err:
            self.lbl_status.setText(f"⚠ {err[:80]}")
            self.lbl_status.setStyleSheet("color: #f85149; font-size: 10px;")
