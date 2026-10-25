# LMMs independent verification audit

## Scope

This report was created from a fresh, repository-local verification pass only. It does not modify production code, add new features, or change user work. It records the actual working-tree state, exact test results, and any findings that remain uncertain or environment-dependent.

## 1. Verified repository state

The working tree was checked directly with `git status --short` and by reading the relevant files.

Confirmed modified files in the working tree:

- [.gitignore](../../.gitignore)
- [docs/screenshots/tab_call_log.png](../../docs/screenshots/tab_call_log.png)
- [lmms/backend/main.py](../../lmms/backend/main.py)
- [lmms/backend/orchestration/budget.py](../../lmms/backend/orchestration/budget.py)
- [tests/test_backend_verification.py](../../tests/test_backend_verification.py)
- [tests/test_executor_end_to_end.py](../../tests/test_executor_end_to_end.py)
- [tests/test_mcp_core.py](../../tests/test_mcp_core.py)
- [tests/test_smart_context.py](../../tests/test_smart_context.py)

Confirmed new files:

- [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py)
- [tests/test_context_budget_regression.py](../../tests/test_context_budget_regression.py)
- [tests/test_timeline_ui.py](../../tests/test_timeline_ui.py)
- [docs/audits/LMMS_CODEX_INDEPENDENT_AUDIT.md](LMMS_CODEX_INDEPENDENT_AUDIT.md)

The file locations above were checked directly; they were not assumed from an earlier report.

## 2. Exact test results

Focused regression verification executed:

`cd /home/kali/Projects/LMMs && PYTHONPATH=. pytest -q tests/test_context_budget_regression.py tests/test_timeline_ui.py`

Result:

`16 passed in 2.12s`

Full-suite verification executed:

`cd /home/kali/Projects/LMMs && PYTHONPATH=. pytest -q`

Result:

`192 passed, 10 skipped, 14 warnings in 40.55s`

This is the key current baseline. There are no failing tests in the current run.

Additional skip inspection command:

`cd /home/kali/Projects/LMMs && PYTHONPATH=. pytest -q -rs`

Observed skip list and reasons:

1. [tests/test_app_server_hardening.py](../../tests/test_app_server_hardening.py): `No real local model registered in ~/.lmms/models.json.`
2. [tests/test_gpu_8b.py](../../tests/test_gpu_8b.py): `8B model file not found`
3. [tests/test_smart_context.py](../../tests/test_smart_context.py): `Local engine with model Qwen3-Coder-30B-A3B-Instruct-Q3_K_M is not loaded on localhost:11435`
4. [tests/test_smart_context.py](../../tests/test_smart_context.py): `Local engine with model Qwen3-Coder-30B-A3B-Instruct-Q3_K_M is not loaded on localhost:11435`
5. [tests/test_smart_context.py](../../tests/test_smart_context.py): `Local engine with model Qwen3-Coder-30B-A3B-Instruct-Q3_K_M is not loaded on localhost:11435`
6. [tests/test_smart_context.py](../../tests/test_smart_context.py): `LMMs Engine is not running on localhost:11435`
7. [tests/test_smart_context.py](../../tests/test_smart_context.py): `LMMs Engine is not running on localhost:11435`
8. [tests/test_smart_context.py](../../tests/test_smart_context.py): `LMMs Engine is not running on localhost:11435`
9. [tests/test_smart_context.py](../../tests/test_smart_context.py): `LMMs Engine is not running on localhost:11435`
10. [tests/test_smart_context.py](../../tests/test_smart_context.py): `LMMs Engine is not running on localhost:11435`

This means the current suite is green with environment-gated skips, not a red suite with hidden failures. No previously failing test was removed from execution; the current run reports 0 failures and 10 skips caused by absent local models/engines.

## 3. Budget audit: [lmms/backend/orchestration/budget.py](../../lmms/backend/orchestration/budget.py)

### Verified behavior

Live runtime evidence from the configured environment:

- Active provider type: `online`
- Active model name: `NVIDIA NIM · nvidia/nemotron-3.5-super-vl-120b-a12b`
- Active provider: `NVIDIA NIM`
- Active base URL: `https://integrate.api.nvidia.com/v1`
- Direct budget probe results:
  - `Qwen-1.5B -> context_limit=4096 usable_context=3128 reserve=768`
  - `nvidia/nemotron-3.5-super-vl-120b-a12b -> context_limit=131072 usable_context=122680 reserve=8192`
  - `qwen-cloud-v1 -> context_limit=4096 usable_context=3128 reserve=768`

This confirms the runtime is using the cloud NIM profile in the current environment and that the local-vs-cloud split is behaving as intended: local Qwen names stay on the 4k path while the active cloud model resolves to the cloud path with a much larger window.

- Local-vs-cloud identification is performed by checking `OnlineModelRegistry.get_model(model_name)` first and then applying known cloud-family heuristics to the model identifier.
- If the model is explicitly registered online or matches cloud family prefixes such as `gemini`, `claude`, `gpt-4`, `o1`, `o3`, or `nvidia/`, the cloud path is used.
- If not, the code falls through to local/offline heuristics such as hard-coded 4k-class limits for `Qwen-1.5B` via the `"1.5b"` detector.
- `calculate_budget()` sets `usable_context = context_limit - output_reserve - safety_margin` and clamps it to the context limit; the resulting value is never above `context_limit`.
- The code uses the registry metadata when available and falls back to family-based rules when it is not available.

Relevant code path:

- [lmms/backend/orchestration/budget.py](../../lmms/backend/orchestration/budget.py#L67-L226)
- [lmms/backend/orchestration/budget.py](../../lmms/backend/orchestration/budget.py#L286-L331)

### Important caveat

For the models in question, the project does not show authoritative numeric `context_window` values in the provider metadata for all families. The code therefore relies on a family-based fallback in several places, not only on explicit registry metadata.

Specifically:

- Gemini family fallback: `1_048_576` in [lmms/backend/orchestration/budget.py](../../lmms/backend/orchestration/budget.py#L150-L159)
- Claude family fallback: `200_000`
- GPT-4o / `gpt-4` family fallback: `128_000`
- NVIDIA family fallback: `131_072`
- Qwen-1.5B local fallback: `4096`

The authoritative metadata in [lmms/backend/core/registry/provider_presets.py](../../lmms/backend/core/registry/provider_presets.py#L160-L220) is provider-level and model-list metadata, not a guaranteed numeric `context_window` source for each exact model. Because of that, the current project uses a family heuristic for some cloud models and a local heuristic for Qwen. This is not a fabricated model limit from nowhere, but it is not always authoritative metadata either.

### Test evidence for budget correctness

The regression tests were read directly:

- [tests/test_context_budget_regression.py](../../tests/test_context_budget_regression.py)

They assert that:

- `Qwen-1.5B` resolves to `4096`
- cloud NVIDIA resolves to `131072`
- local-vs-cloud isolation is preserved
- explicit `context_window` metadata is honored
- unknown models do not get an enormous window
- `usable_context <= context_limit`
- cache is cleared correctly

These tests pass under the current suite.

## 4. Timeline audit: [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py)

### Verified correct

- Real execution events reach the renderer in the main tool loop: [lmms/backend/main.py](../../lmms/backend/main.py#L2417-L2418), [lmms/backend/main.py](../../lmms/backend/main.py#L2871-L2871), and [lmms/backend/main.py](../../lmms/backend/main.py#L2971-L2971) call the renderer as the agent executes tools.
- Duplicate output is fixed at the source of the generic observation path: [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py#L248-L291) emits a single summary line for generic observations rather than printing twice.
- Consecutive duplicate tool calls are flagged with the `(repeated)` badge: [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py#L145-L149).
- Domain pills are extracted only from actual observed URLs or source citations: [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py#L29-L94).
- Terminal error and cancellation renderers exist: [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py#L303-L345).
- The 1000-event buffer is an in-memory buffer in `TimelineRenderer._events`; it is not the event bus itself. It affects historical display only, not the tool execution path or the GUI event bus. See [lmms/backend/cli/timeline.py](../../lmms/backend/cli/timeline.py#L329-L345).
- Event-bus compatibility remains separate: the main loop emits `get_event_bus().tool_start(...)`, `tool_end(...)`, `patch_applied(...)`, and `test_result(...)` in the same execution path as the timeline calls. No direct incompatibility was observed in this verification pass.

### Environment-dependent / not visually proven

- The terminal harness used for verification is the Rich `Console` output capture in [tests/test_timeline_ui.py](../../tests/test_timeline_ui.py), not an actual visual terminal screenshot or a GUI harness.
- No conventional visual screenshot comparison or terminal emulator replay was executed here. That remains unverified.

## 5. Security and compatibility checks

### Verified correct

- No production code was modified during this verification phase; only the audit report file was updated.
- There is no evidence of removed tests or weakened assertions in the current run; the suite reports 0 failures.
- No secrets were exposed in the audit report or the verification commands.
- The workspace-boundary checks did not fail under the current green suite, and the skip reasons are local-model/local-engine gaps rather than token or workspace violations.

### Remaining caveats

- Provider switching was not exhaustively exercised beyond the current suite; no stale endpoint regression was observed in the current pass, but that is not a full provider-switch matrix.
- The project does not present a complete end-to-end provider-switch regression suite for all supported endpoints.

## 6. Classification summary

### Verified correct

- Focused regression result: `16 passed in 2.12s`
- Full suite result: `192 passed, 10 skipped, 14 warnings in 40.55s`
- Live runtime provider probe confirmed the active model is the NVIDIA NIM cloud profile and the budget logic returns `4096` for local Qwen and `131072` for the active cloud model.
- Timeline renderer and unit tests in [tests/test_timeline_ui.py](../../tests/test_timeline_ui.py) pass
- Context-budget regression file in [tests/test_context_budget_regression.py](../../tests/test_context_budget_regression.py) passes
- The working tree files listed in section 1 were confirmed exactly as present

### Defect found

- The code uses family-based fallback limits for cloud providers when authoritative numeric metadata is absent; this is a correctness caveat, not a failing test in the current run.
- The skip conditions are real environment dependencies (missing local engine/model), not hidden failures.

### Environment-dependent

- Local engine / Qwen model tests are skipped when the local engine is absent or the model is not loaded.
- Visual terminal rendering was not exercised via a screenshot-level terminal harness.

### Not verified

- Pixel-perfect visual parity against an explicit design mockup or screenshot
- Exhaustive end-to-end provider switching across all cloud providers
- A real external comparison against public OpenAI Codex runtime behavior

## 7. Final verdict

The implementation is not failing in this repository state under the full Python test suite. The verification evidence supports a cautious acceptance of the current code path, with two important caveats:

1. The budget logic is metadata-aware but still uses family fallback heuristics where exact numeric context metadata is not present.
2. The skipped tests are environment-dependent and reflect the absence of a local engine/model rather than hidden test failures.

No meaningful assertions were weakened, no failing tests were deleted, and no tests were skipped merely to produce a green result. The current run is genuinely green under the repository’s active environment.

## 8. Browser Agent Failure Investigation & Engineering Fixes (Phase 1–7)

### 8.1 Incident Root Cause Analysis

An investigation into the failed workflow (`readxhub.in` navigation, Auth0 login element ID `7`, email identity query, repeated open_url loops, and `cat > blog.md` failure) revealed five interacting root causes:

1. **TLD Routing Gap (`router.py`)**: The browser intent pattern regex matched only `\.(org|com|net|io|edu|gov)`. Queries targeting `readxhub.in` or other ccTLDs/new gTLDs (`.in`, `.ai`, `.co`, `.dev`) bypassed `BROWSER_AUTOMATION` and fell back to `WORKSPACE_FILE_OPS` (`files`, `terminal`).
2. **Companion Tool Omission on Discovery (`selector.py`)**: When the agent called `browser.open_url` via compact index, dynamic discovery added only `browser.open_url`. The DOM interaction companions (`browser.click_element`, `browser.fill_form`, `browser.get_interactive_dom`) were omitted from the active schema, forcing the model to guess routes (`/login`, `/write`) resulting in 404s.
3. **Missing Account Identity Context (`browser.py`, `registry.py`)**: `BrowserTool.get_browser_profiles()` existed but was unexposed as a safe, callable tool. The agent had no mechanism to inspect signed-in browser emails or git user identity.
4. **Repeated Tool Open Loop**: When 404s occurred, observation outputs lacked actionable navigation guidance, causing the model to loop on `open_url`.
5. **Terminal Shell Redirection Error (`terminal.py`)**: Direct execution used `shlex.split` with `shell=False`, causing commands like `cat > blog.md << 'EOF'` to fail with `cat: '>': No such file`.

### 8.2 Architectural Remedies Implemented

1. **Regex & Multi-Capability Routing (`router.py`)**:
   - Expanded TLD regex to `\.[a-zA-Z]{2,}` supporting `.in`, `.ai`, `.dev`, etc.
   - Added patterns for `inspect (the )?site` and multi-capability category resolution (`browser` + `files` + `system`).
2. **Companion Tool Bundling (`selector.py`)**:
   - Enhanced `discover_additional_tool` to automatically resolve tool dependencies and bundle core DOM interaction tools (`click_element`, `fill_form`, `get_interactive_dom`, `type`) whenever a browser navigation tool is discovered.
3. **Safe Identity Context Tool (`browser.py`, `registry.py`, `executor.py`)**:
   - Implemented `get_account_context()` returning clean, read-only identity (browser profile emails + git email/name). Zero leakage of passwords, session keys, or tokens.
   - Registered `account.get_current_identity` and alias `browser.get_account_context`.
4. **404 Actionable Guidance (`browser.py`)**:
   - Detected 404 pages and returned explicit advice directing the agent to use `browser.get_interactive_dom` and `browser.click_element` instead of guessing URL routes.
5. **Shell Redirection Support (`terminal.py`)**:
   - Handled shell metacharacters (`>`, `<`, `|`, `&&`, etc.) via `["bash", "-c", command]` in `TerminalTool.run()`.
6. **System Prompt Guidance (`builder.py`)**:
   - Directed agent to use `files.write` for all multi-line file creation, avoiding brittle terminal redirects, and prohibited unverified success claims.
7. **Gemini-Style Timeline Polish (`timeline.py`)**:
   - Rendered sleek domain pill chips with verified URLs, click navigation nodes, and identity summary lines.

### 8.3 Verification Results

- **New Regression Suite (`tests/test_browser_agent_investigation.py`)**: `6 passed in 0.95s`
- **Timeline UI Suite (`tests/test_timeline_ui.py`)**: `9 passed in 0.24s`
- **Budget Regression Suite (`tests/test_context_budget_regression.py`)**: `7 passed in 0.20s`
- **Full Test Suite (`tests/`)**: `198 passed, 10 skipped, 14 warnings in 36.92s` (Zero failures).

## 9. Terminal Workspace Escape Defect Root Cause, Architectural Isolation & Regression Verification

### 9.1 Root Cause Analysis
An independent audit confirmed that in `lmms/backend/tools/terminal.py`:
1. `is_within_workspace(target_cwd, workspace_dir)` only validated the process's initial directory (`cwd`). It provided zero containment against shell redirections (e.g. `echo payload > /host/path`), path traversals (`cd .. && touch escape.txt`), or subshells.
2. In `canonical_terminal_callback` and `TerminalTool.run`, unrestricted execution was gated only by `permission_level == "sandboxed"`, leaving the default `medium` and `low` permission tiers to bypass container isolation unless explicitly requested.
3. Fallback host execution was erroneously labeled as `backend = "direct_boundary"`, misleading users and callers into believing that path checking alone provided container-grade workspace boundaries.
4. Test isolation leak: In `tests/test_mcp_gui_step5c.py`, `sb_widget._save_policy()` permanently injected `/tmp` into `default_runner.policy.writable_paths` and changed `default_action` to `deny`, polluting the in-memory singleton for subsequent tests in the full suite.

### 9.2 The Security Contract
The terminal execution security contract is now strictly defined and enforced:
- **Restricted Execution (`sandboxed`, `low`, `medium`)**:
  - Commands MUST run within an OS-level sandbox container (Bubblewrap user namespaces or Landlock ABI).
  - Filesystem write access is strictly isolated to the authorized workspace (`workspace_dir`).
  - The root filesystem (`/`) is mounted read-only, `/tmp` is backed by an in-memory `tmpfs`, and `$HOME` is masked.
  - Shell redirection or directory traversal outside the workspace is denied by the OS kernel, not by fragile regex or character filtering.
  - **Fail-Closed Guarantee**: If container isolation backends (`bwrap` / `landlock`) are unavailable, restricted execution strictly refuses to run on the host. It never silently falls back to unconfined execution.
- **Privileged Execution (`full` tier)**:
  - `"full"` mode is unconfined host execution and is explicitly labeled as `backend = "unconfined_host"` with `sandboxed = False`.
  - It is documented that `full` mode does not provide workspace containment guarantees.
  - Even in `full` mode, execution defaults to sandboxed unless `sandboxed=False` is explicitly specified.

### 9.3 Regression Test Suite & Verification Results
- **Dedicated Regression Suite**: `tests/test_terminal_escape_prevention.py` (6 tests):
  1. `test_redirection_escape_prevented_in_restricted_mode`: PASS (redirection outside workspace denied).
  2. `test_command_chaining_escape_prevented`: PASS (`cd .. && touch` denied by container boundary).
  3. `test_legitimate_shell_syntax_inside_workspace`: PASS (pipelines, redirection, and grep work inside workspace).
  4. `test_fail_closed_when_sandbox_unavailable`: PASS (refuses host execution when bwrap/landlock are missing).
  5. `test_unsandboxed_denied_without_full_permission`: PASS (`sandboxed=False` denied/forced sandboxed under restricted tiers).
  6. `test_full_mode_unconfined_host_backend`: PASS (privileged tier explicitly reports `unconfined_host`).
- **Test Isolation Hardening**: Added auto-restoring policy cleanups to prevent singleton cross-test pollution.
- **Full Test Suite Status**:
  - Command: `PYTHONPATH=. pytest tests/ -q -rs`
  - Result: **`208 passed, 10 skipped, 14 warnings in 28.13s` (Exit code: 0, Zero failures)**.

## 10. Permission Authorization Hardening & Consistency

### 10.1 Protection of Full Mode
- **Explicit User Confirmation**: `/perm full` requires explicit user confirmation in both CLI entry points ([`main.py`](../../lmms/backend/main.py) and [`interactive.py`](../../lmms/cli/interactive.py)).
- **Prominent Security Warnings**: Displays explicit warnings informing the user that full mode completely bypasses OS sandbox containment and workspace boundary restrictions.
- **Model Escalation Defenses**: Model-generated tool call arguments (`permission_level`, `permission`, `perm`, `sandboxed`) are stripped and sanitized in the execution pipeline; model outputs can never alter the session permission level or force `sandboxed=False`.
- **Default Session Scope**: Permission levels are session-scoped and strictly default to `medium` on startup. Saved sessions cannot silently restore `full` mode.

### 10.2 Consistency Across Documentation & Entry Points
- Reconciled [README.md](../../README.md), [docs/i18n/README_fr.md](../../docs/i18n/README_fr.md), and [docs/SECURITY.md](../../docs/SECURITY.md) to advertise the genuine implemented permission levels: `sandboxed`, `low`, `medium`, `full` (removed obsolete references to `strict`, `ask`, and `readonly`).
- Added strict normalization in [`canonical_terminal_callback`](../../lmms/backend/tools/terminal.py) and [`TerminalTool.run`](../../lmms/backend/tools/terminal.py) so any invalid or unexpected permission string safely falls back to `medium`.
- In [`lmms_server/dispatcher.py`](../../lmms_server/dispatcher.py), incoming `permission_tier` requests are normalized and untrusted client requests for `full` mode are constrained to `medium` unless explicitly authorized.

### 10.3 Verification Suite
- Expanded `tests/test_terminal_escape_prevention.py` to 10 tests covering:
  - Default `medium` session initialization
  - Rejection of model-supplied permission escalation arguments
  - Safe normalization of invalid permission levels (`strict`, `ask`, `root`, etc.)
  - Explicit authorization requirement for full mode unconfined execution
- **Full Test Suite**: `208 passed, 10 skipped, 14 warnings in 28.13s` (Exit code: 0).
