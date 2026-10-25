# COPILOT TERMINAL FILE EXECUTION AUDIT

## Scope and method

This is a read-only audit of the implementation that governs terminal execution, workspace file writes, and tool-call validation in LMMs. The goal was to determine why a legitimate request could fail even when the user believed permissions were enabled, without assuming prior conclusions.

No production code or configuration was modified as part of this audit.

---

## Executive summary

The implementation is intentionally fail-closed for shell metacharacters and command chaining. The exact rejection point is the shell command parser, which blocks patterns such as `;`, `&&`, `||`, `|`, `>`, `<`, `$()`, backticks, `sudo`, `bash`, `sh`, and `eval` before the command is executed.

This means a legitimate workflow that relies on command chaining or shell redirection is not just “a minor bug”; it is an explicit security rule. The user’s observed “`&&` denied” behavior matches the current implementation.

Separately, the file-write path is protected by workspace boundary checks and read-back integrity verification, which is a real safeguard. The app does not appear to silently write outside the workspace without validation.

The `message.send` tool also has a strict schema: it requires a `message` field. A call that omits it is rejected by the tool registry/runtime validation path before any message is sent.

The broad takeaway is: the system is secure by design, but the security model is stricter than the user’s expectation. Legitimate file-generation or command-composition workflows are blocked by explicit deny rules, and the code path can produce a misleading user-facing impression if the model or the caller does not surface the exact reason.

---

## Verified finding 1: the exact rejection of `&&` is intentional

Primary evidence:

- [LMMs/lmms/backend/security/command_parser.py](../../lmms/backend/security/command_parser.py)

Relevant logic:

```python
# Check for dangerous shell constructs
dangerous_patterns = [
    r";",           # Command chaining
    r"&&",          # Logical AND
    r"\|\|",        # Logical OR
    r"\|",          # Pipes
    r">",           # Redirection
    r"<",           # Redirection
    r"\$\(",        # Subshell execution
    r"`",           # Subshell backticks
    r"&(?!\w)",     # Background execution
    r"\benv\b",     # env override
    r"\bsudo\b",    # Privilege escalation
    r"\bsu\b",      # Privilege escalation
    r"\bbash\b",    # Nested shell
    r"\bsh\b",      # Nested shell
    r"\bzsh\b",     # Nested shell
    r"\beval\b"     # Evaluation
]

for pattern in dangerous_patterns:
    if re.search(pattern, command):
        raise CommandParserError(f"Command contains blocked shell construct matching pattern: {pattern}")
```

This is not a random parser bug; it is a deliberate denylist that rejects multi-command execution before any shell command runs.

---

## Verified finding 2: terminal permission checks reject the command before execution

Primary evidence:

- [LMMs/lmms/backend/security/permission_manager.py](../../lmms/backend/security/permission_manager.py)

Relevant logic:

```python
if request.tool_name == "terminal.run":
    command = request.kwargs.get("command", "")
    from lmms_sandbox.runner import default_runner
    pol_res = default_runner.evaluate_command(command)
    ...

    try:
        parsed_cmds = parse_shell_command(command)
    except CommandParserError as e:
        return PermissionResult(allowed=False, reason=str(e), risk_level="critical")
```

This means all terminal execution is routed through policy evaluation and shell parsing. If the command contains a blocked shell construct, the permission layer denies it with a `critical` risk result.

This is the exact path that explains why a request like `cd .. && ...` or a similar multi-step command is rejected.

---

## Verified finding 3: restricted execution is designed to be sandboxed and fail-closed

Primary evidence:

- [LMMs/lmms/backend/tools/terminal.py](../../lmms/backend/tools/terminal.py)
- [LMMs/lmms/backend/security/executor.py](../../lmms/backend/security/executor.py)
- [LMMs/lmms_sandbox/runner.py](../../lmms_sandbox/runner.py)
- [LMMs/lmms_sandbox/policy.py](../../lmms_sandbox/policy.py)

The tool enforces a strict security model:

- Restricted modes (`sandboxed`, `low`, `medium`) require sandboxed execution.
- A direct un-sandboxed host execution is refused unless the permission level is explicitly `full`.
- If the sandbox backend is unavailable, the app fails closed instead of executing on the host.

Relevant terminal logic:

```python
if perm_level != "full":
    # In restricted modes (sandboxed, low, medium), execution MUST be sandboxed
    effective_sandboxed = True

if effective_sandboxed:
    from lmms_sandbox.runner import default_runner
    res = default_runner.run(..., enforce_sandbox=True)
    ...

if perm_level != "full":
    raise PermissionError(
        "REFUSED: Direct un-sandboxed execution on host is blocked."
    )
```

This is by design and it does not indicate a hidden permission bug. It means the user’s “I enabled permissions” expectation is not the same as the system’s actual policy model.

---

## Verified finding 4: full-mode execution is explicit and not silent

Primary evidence:

- [LMMs/lmms/cli/interactive.py](../../lmms/cli/interactive.py)

The CLI permission flow does not silently escalate to full host execution. It requires an explicit mode change such as `/perm full`, and the code warns that it is unconfined:

```python
if cmd == "/perm":
    ...
    # full mode is a deliberate override, not implicit auth
```

The code path in the terminal tool also only allows unconfined host execution when the permission tier is `full` and the sandbox flag is set appropriately.

This is important: the implementation is not claiming “permissions are fully enabled” by default. It enforces a staged authorization model.

---

## Verified finding 5: file writes are bounded and verified; they are not silent file writes to arbitrary paths

Primary evidence:

- [LMMs/lmms/backend/tools/files.py](../../lmms/backend/tools/files.py)
- [LMMs/lmms/backend/tools/boundaries.py](../../lmms/backend/tools/boundaries.py)

The file-write implementation performs path validation and read-back verification:

```python
resolved_path = enforce_boundary(path)
...
with open(resolved_path, "w", encoding="utf-8") as f:
    f.write(content)
    f.flush()
    os.fsync(f.fileno())

with open(resolved_path, "r", encoding="utf-8") as rf:
    persisted = rf.read()

if persisted == content and persisted_sha == expected_sha:
    ...
    return True, msg, stats
```

The boundary check is:

```python
def require_workspace_path(path: str, workspace: str) -> str:
    if not os.path.isabs(path):
        target = os.path.join(workspace, path)
    else:
        target = path

    if not is_within_workspace(target, workspace):
        raise PermissionError(f"Path {path} is outside the allowed workspace boundary.")
    return os.path.realpath(os.path.abspath(target))
```

This confirms that file writes are intended to be workspace-scoped and verified. The write path is not a blanket “allow any file anywhere” path.

---

## Verified finding 6: the schema for `message.send` requires a `message` field

Primary evidence:

- [LMMs/lmms/backend/orchestration/registry.py](../../lmms/backend/orchestration/registry.py)
- [LMMs/lmms/backend/tools/messenger.py](../../lmms/backend/tools/messenger.py)

The tool schema is explicit:

```python
parameters={
    "type": "object",
    "properties": {
        "platform": {"type": "string", "default": "desktop"},
        "message": {"type": "string", "description": "Notification message body"},
        "recipient": {"type": "string", "description": "Optional recipient or notification title"}
    },
    "required": ["message"]
}
```

This means a `message.send` call without `message` is invalid by contract. This is a tool-validation issue, not a runtime permission issue.

A model or caller sending a malformed payload cannot satisfy the required schema and the request is rejected before a notification is sent.

---

## Why legitimate tasks fail in practice

A legitimate user task can fail for two different reasons that are easy to conflate:

1. Security denial
   - The command contains shell metacharacters or chaining, and the parser denies it.
   - Example: `&&`, `|`, `>`, `;`, `$()`, backticks, `bash -c` style flows.

2. Tool-contract validation failure
   - The tool request is structurally invalid, e.g. `message.send` without a `message` field.

3. False-confidence from the model layer
   - The system may present a claim that a file was written or a task completed without a verified tool observation.
   - The code does not blindly assume success; file writes are explicitly verified, but the surrounding orchestration can still surface a misleading narrative if the model does not surface the actual tool result.

This is precisely why “I asked for a landing page at /home/kali/development/index.html” can turn into a blocked shell command plus an unmatched success claim, even though the file system and permission boundaries are working as designed.

---

## Existing tests and what they confirm

Relevant tests reinforce the interpretation rather than contradict it:

- [LMMs/tests/test_terminal_escape_prevention.py](../../tests/test_terminal_escape_prevention.py)
- [LMMs/tests/test_file_writing_reliability.py](../../tests/test_file_writing_reliability.py)

The terminal escape-prevention tests explicitly assert that:

- redirected writes outside the workspace are prevented in restricted mode,
- chained commands such as `cd .. && ...` are prevented,
- legitimate shell syntax is allowed only inside sandboxed workspace boundaries,
- unconfined host execution is denied unless explicit `full` mode is used.

The file-writing tests explicitly verify read-back integrity and `FILE_WRITE_VERIFIED` success reporting.

This is consistent with the security model and indicates the implementation is intentionally restrictive rather than accidentally broken.

---

## Conclusion

The observed behavior is consistent with the actual code:

- shell chaining and redirection are blocked intentionally,
- terminal execution is policy-gated and environment-limited,
- full host execution is explicit and not a default permission grant,
- file writes are workspace-scoped and verified,
- malformed tool calls are rejected by schema validation.

The most important takeaway is not “permissions are broken,” but rather “the current implementation enforces a strong security policy that rejects the kinds of commands and tool payloads that the user expected to work.”

---

## Highest-priority fixes for the implementation agent

1. Narrow the shell denylist to truly dangerous cases while preserving safe, user-approved command patterns.
   - Avoid treating legitimate multi-step commands as categorically blocked when they are within the workspace and part of an approved workflow.

2. Return structured denial reasons to the model layer and fallback instructions, instead of letting the model continue with a misleading success narrative.
   - Example: “Command blocked by shell parser for `&&`; allowed alternatives: use file.write or a single safe command.”

3. Add explicit validation feedback for malformed tool calls.
   - For `message.send`, return a clear schema error and do not allow a silent partial call.

4. Add end-to-end regression tests for:
   - a legitimate workspace-scoped file creation flow,
   - a blocked chained command returning a clear failure reason,
   - a malformed `message.send` JSON payload,
   - a full-mode explicit approval flow.

5. Preserve the current security boundaries, but improve the user-visible contract so it clearly distinguishes:
   - security denial,
   - permission escalation required,
   - invalid tool schema,
   - verified file-write success.

These are the highest-value fixes because they preserve the security model while reducing false expectations and ambiguous tool failures.
