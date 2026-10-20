# LMMs Security Model & Isolation Boundaries

## 1. Overview: Defense in Depth

LMMs employs a multi-tiered security model designed to provide safe offline tool and command execution for autonomous coding agents:

1. **Permission Tiers (`/perm ask | allow | sandboxed | readonly`)**: High-level permission mode controlling tool access and gating dangerous actions.
2. **Execution Policy (`~/.lmms/execpolicy.toml`)**: First-layer pre-execution heuristic filter.
3. **OS-Level Sandbox Containment (Bubblewrap & Landlock LSM)**: Kernel isolation boundary providing genuine hardware/filesystem/network containment.
4. **Git Worktree Isolation (`/worktree on`)**: Ephemeral workspace preventing direct modifications to the user's primary working tree.

---

## 2. ExecPolicy: A Best-Effort Heuristic Filter, Not a Sandbox Boundary

> [!WARNING]
> **ExecPolicy is an advisory, first-layer filter—not a security boundary.**
> The real containment is provided exclusively by OS-level sandboxing (Bubblewrap namespaces and Linux Landlock LSM).

The `ExecPolicy` engine inspects command strings against configurable rule sets (`deny`, `ask`, `allow`), and decomposes shell compounds (`&&`, `||`, `;`, pipes, and command substitutions `$(...)` / backticks). However, in dynamic shell and scripting environments, static pattern matching can inherently be bypassed by Turing-complete interpreters and obfuscation techniques.

### Known Bypass Classes for Static Command Filters

If a command is allowed to execute without sandbox containment, an agent or script could construct operations that evade string-based filters:

1. **Interpreter Eval & Dynamic Execution**:
   - `python3 -c "import os; os.system('...')"`
   - `perl -e 'unlink ...'`
   - `ruby -e '...'`
   - `node -e 'require("child_process").execSync("...")'`
2. **Shell Dynamic Evaluation**:
   - `eval "$encoded_command"`
   - `source <(curl -s ...)`
   - `bash < <(base64 -d payload)`
3. **Encoding & De-obfuscation Pipelines**:
   - `echo <base64_blob> | base64 -d | sh`
   - `printf '\x72\x6d\x20\x2d\x72\x66\x20...' | bash`
4. **Utility Invocations with Inherent Execution Capabilities**:
   - `find . -name "*.txt" -delete` (file deletion without explicit `rm`)
   - `find / -exec <cmd> {} +`
   - `xargs -I {} rm {}`
   - `awk 'BEGIN { system("...") }'`
   - `vim -c ':!bash'`
5. **Symlink and Path Traversal Exploits**:
   - Creating symlinks inside the workspace pointing outside, then operating through the symlink.
   - Manipulation of environment variables (`LD_PRELOAD`, `PATH`, `PYTHONPATH`).

---

## 3. The True Security Boundary: Linux Kernel Isolation

Real isolation is achieved only when OS-level containment mechanisms are active:

### Bubblewrap (`bwrap`)
- **Filesystem Isolation**: Mounts `/` read-only (`--ro-bind / /`), masks the user's `$HOME` with a clean `tmpfs`, and exposes only the designated workspace directory as writable.
- **Credential Protection**: Deny-by-default isolation hides `~/.ssh`, `~/.netrc`, `~/.aws`, `~/.config`, and shell histories from child execution.
- **Process & PID Isolation**: `--die-with-parent`, `--new-session`, and separate `/proc` and `/dev`.
- **Network Containment**: `--unshare-net` drops all network interfaces, preventing unexpected data exfiltration or external socket creation.

### Landlock LSM (Unprivileged Linux Security Module)
- Fallback kernel LSM restriction applied via Linux syscalls (`SYS_landlock_create_ruleset`, `SYS_landlock_add_rule`, `SYS_landlock_restrict_self`).
- Sets `PR_SET_NO_NEW_PRIVS` to prevent privilege escalation.
- Applied in child processes via dedicated launcher (`lmms_sandbox.landlock_launcher`), guaranteeing the main multi-threaded LMMs process is never restricted or deadlocked.

---

## 4. Git Worktree & Session Safety

- **Worktree Isolation**: Sandboxed agent edits are confined to `/tmp/lmms_worktrees/` on an ephemeral branch (`lmms-wt-*`). The user's main branch and working tree are completely isolated from unreviewed agent modifications until explicit `/worktree apply`.
- **Atomic Checkpoints**: Automatic checkpoints use an independent `GIT_INDEX_FILE` environment variable, ensuring the user's current index and dirty working tree are never modified, stashed, or reset.
