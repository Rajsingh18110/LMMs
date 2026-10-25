"""
CompletionGuard: Centralized orchestrator-level invariant enforcer.
Ensures that denied, failed, or unverified tool operations can never be represented
as verified successes in the agent's final response or internal state.
"""

import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set


class ToolExecutionStatus(str, Enum):
    SUCCESS = "success"        # Genuinely executed and verified on disk or live session
    DENIED = "denied"          # Blocked by security policy, boundaries, or approval gates
    FAILED = "failed"          # Execution error, non-zero exit code, or integrity check failure
    UNVERIFIED = "unverified"  # Action triggered but persistence / effect could not be confirmed


@dataclass
class OperationRecord:
    tool_name: str
    target: str
    target_basename: str
    status: ToolExecutionStatus
    verified: bool
    reason_or_error: str = ""
    output_snippet: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardResult:
    is_valid: bool
    guarded_text: str
    false_claims_detected: List[str]
    unresolved_failures: List[OperationRecord]
    verified_successes: List[OperationRecord]
    correction_applied: bool


def extract_target_from_call(tool_name: str, kwargs: Dict[str, Any]) -> Tuple[str, str]:
    """
    Extracts canonical target identifier and its basename from tool kwargs.
    Returns (target, target_basename).
    """
    if not kwargs or not isinstance(kwargs, dict):
        return "", ""

    target = ""
    # 1. File paths
    for k in ("path", "file_path", "filepath", "filename", "file", "target_file"):
        if k in kwargs and kwargs[k]:
            target = str(kwargs[k]).strip()
            break

    # 2. Terminal commands
    if not target:
        for k in ("command", "cmd", "shell_command"):
            if k in kwargs and kwargs[k]:
                cmd = str(kwargs[k]).strip()
                target = cmd
                break

    # 3. Browser elements / URLs
    if not target:
        for k in ("selector", "target", "element", "url", "link", "target_url"):
            if k in kwargs and kwargs[k]:
                target = str(kwargs[k]).strip()
                break

    # 4. Message recipients
    if not target:
        for k in ("recipient", "target", "channel", "chat_id", "to"):
            if k in kwargs and kwargs[k]:
                target = str(kwargs[k]).strip()
                break

    basename = os.path.basename(target) if target and "/" in target else target
    return target, basename


class CompletionGuard:
    """
    Centralized completion invariant guard.
    Guarantees:
    1. A denied, failed, or unverified operation is never represented as verified success.
    2. Legitimate retries and alternative routes that succeed are recognized as resolved.
    3. Unrelated informational responses are not blocked.
    4. Partial completion reports succeeded and failed components distinctly.
    """

    def __init__(self):
        self.operations: List[OperationRecord] = []

    def start_turn(self):
        """Clears turn-scoped operation records at the start of a user turn."""
        self.operations = []

    def record_operation(
        self,
        tool_name: str,
        kwargs: Optional[Dict[str, Any]] = None,
        status: ToolExecutionStatus = ToolExecutionStatus.FAILED,
        verified: bool = False,
        reason_or_error: str = "",
        output_snippet: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        *,
        arguments: Optional[Dict[str, Any]] = None,
        error_snippet: str = "",
        **extra_kwargs: Any
    ) -> OperationRecord:
        """Records an authoritative operation execution record."""
        effective_kwargs = kwargs if kwargs is not None else (arguments if arguments is not None else {})
        effective_reason = reason_or_error or error_snippet or extra_kwargs.get("error", "")
        target, basename = extract_target_from_call(tool_name, effective_kwargs)
        
        # Normalize status enum
        if isinstance(status, str):
            try:
                status = ToolExecutionStatus(status.lower())
            except ValueError:
                status = ToolExecutionStatus.FAILED

        # Double-check file write verification invariant
        if tool_name in ("files.write", "file.write", "write_file", "write_to_file"):
            if status == ToolExecutionStatus.SUCCESS and not verified:
                status = ToolExecutionStatus.UNVERIFIED

        rec = OperationRecord(
            tool_name=tool_name,
            target=target,
            target_basename=basename,
            status=status,
            verified=bool(verified),
            reason_or_error=effective_reason,
            output_snippet=output_snippet[:300] if output_snippet else "",
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self.operations.append(rec)
        return rec

    def is_target_resolved(self, target: str, basename: str) -> Tuple[bool, Optional[OperationRecord]]:
        """
        Determines whether a target that previously failed was subsequently resolved
        by a successful, verified operation in the same turn/context.
        """
        matching = [
            op for op in self.operations
            if (target and op.target == target) or (basename and op.target_basename == basename)
        ]
        if not matching:
            return False, None

        # Check if the latest operation or any operation for this target was verified success
        for op in reversed(matching):
            if op.status == ToolExecutionStatus.SUCCESS and op.verified:
                return True, op

        return False, matching[-1]

    def get_unresolved_failures(self) -> List[OperationRecord]:
        """
        Returns list of operations that were denied, failed, or unverified
        and have NOT been superseded by a verified success for the same target.
        """
        unresolved: Dict[str, OperationRecord] = {}
        resolved_keys: Set[str] = set()

        for op in self.operations:
            key = op.target or op.target_basename or op.tool_name
            if op.status == ToolExecutionStatus.SUCCESS and op.verified:
                resolved_keys.add(key)
                if key in unresolved:
                    del unresolved[key]
            else:
                if key not in resolved_keys:
                    unresolved[key] = op

        return list(unresolved.values())

    def get_verified_successes(self) -> List[OperationRecord]:
        """Returns all operations that genuinely succeeded with verified evidence."""
        successes: Dict[str, OperationRecord] = {}
        for op in self.operations:
            if op.status == ToolExecutionStatus.SUCCESS and op.verified:
                key = op.target or op.target_basename or op.tool_name
                successes[key] = op
        return list(successes.values())

    def detect_false_success_claims(self, text: str) -> List[Tuple[OperationRecord, str]]:
        """
        Scans proposed response text for false success claims regarding unresolved failures.
        Returns list of (failed_record, matched_phrase).
        """
        unresolved = self.get_unresolved_failures()
        if not unresolved or not text:
            return []

        false_claims: List[Tuple[OperationRecord, str]] = []

        # Affirmative creation / execution verbs
        affirmative_patterns = [
            r"\b(?:i have|i've|have|successfully|we have)\s+(?:created|written|saved|generated|built|added|installed|executed|published|updated|modified|applied|edited)\b",
            r"\b(?:has been|is now|was)\s+(?:created|written|saved|generated|built|added|installed|executed|published|updated|modified|applied|edited)\b",
            r"\b(?:created|wrote|saved|generated|published|updated|modified|applied)\s+(?:the|your|a)?\s*(?:file|draft|post|document|script|page|changes)\b",
            r"\b(?:i\s+)?(?:created|wrote|saved|generated|built|added|installed|executed|published|updated)\b",
            r"\b(?:ready|done|finished|complete|set up)\s+at\b",
            r"\b(?:file|draft|post|document|script)\s+(?:is|has been)\s+(?:created|saved|written)\b",
            r"\ball set\b",
        ]

        # Negation / honest reporting indicators
        negation_patterns = [
            r"\b(?:could not|failed to|unable to|cannot|denied|blocked|error|rejected|was not|not created|did not create)\b",
            r"\b(?:attempted to|prevented|violation|forbidden|refused)\b",
        ]

        def extract_clause(src: str, start_pos: int, end_pos: int) -> str:
            # Look backwards for true sentence boundary: newline or period followed by whitespace and capital
            left_part = src[:start_pos]
            b_left = [m.end() for m in re.finditer(r'(?:[\n]|\.\s+(?=[A-Z0-9]))', left_part)]
            c_start = b_left[-1] if b_left else 0

            # Look forwards for sentence boundary
            right_part = src[end_pos:]
            m_right = re.search(r'(?:[\n]|\.\s+(?=[A-Z0-9])|\.$|\n)', right_part)
            c_end = end_pos + m_right.start() if m_right else len(src)
            return src[c_start:c_end].strip()

        for op in unresolved:
            target_identifiers = []
            if op.target_basename and len(op.target_basename) > 2:
                target_identifiers.append(re.escape(op.target_basename))
            if op.target and op.target != op.target_basename and len(op.target) > 3:
                target_identifiers.append(re.escape(op.target))

            if not target_identifiers and "file" in op.tool_name:
                target_identifiers.append(r"\bfile\b")

            if op.tool_name in ("browser.save_draft", "browser.request_publication_approval"):
                target_identifiers.append(r"\b(?:draft|post|article)\b")

            for tid in target_identifiers:
                for match in re.finditer(tid, text, re.IGNORECASE):
                    clause = extract_clause(text, match.start(), match.end())
                    if not clause:
                        continue

                    has_negation = any(re.search(neg, clause, re.IGNORECASE) for neg in negation_patterns)
                    if has_negation:
                        continue

                    has_affirmative = any(re.search(aff, clause, re.IGNORECASE) for aff in affirmative_patterns)
                    if has_affirmative:
                        false_claims.append((op, clause))
                        break
                if any(fc[0] == op for fc in false_claims):
                    break

        return false_claims

    def validate_and_guard(
        self,
        proposed_response: str,
        user_prompt: str = "",
        workspace: str = ""
    ) -> Tuple[str, GuardResult]:
        """
        Validates the proposed assistant response against actual execution evidence.
        If a false success claim is detected, intercepts and corrects the response.
        """
        unresolved = self.get_unresolved_failures()
        verified = self.get_verified_successes()
        false_claims = self.detect_false_success_claims(proposed_response)

        if not false_claims:
            # Response is truthful or unrelated: allow without modification
            res = GuardResult(
                is_valid=True,
                guarded_text=proposed_response,
                false_claims_detected=[],
                unresolved_failures=unresolved,
                verified_successes=verified,
                correction_applied=False
            )
            return proposed_response, res

        # False claims detected: construct authoritative, honest response
        lines = []
        is_partial = len(verified) > 0

        if is_partial:
            lines.append("### [COMPLETION_GUARD] Task Partially Completed\n")
            lines.append("The requested task was only partially completed. The system verified some actions, but others were blocked or failed:\n")
            lines.append("**Verified Successful Operations:**")
            for v in verified:
                detail = v.output_snippet or "Verified successfully on disk."
                lines.append(f"- **`{v.tool_name}`** (`{v.target}`): {detail}")
            lines.append("\n**Failed / Denied Operations:**")
            for f_rec in unresolved:
                reason = f_rec.reason_or_error or "Execution failed or was denied by policy."
                lines.append(f"- **`{f_rec.tool_name}`** (`{f_rec.target}`): {reason}")
            lines.append("\n> **Important:** Only the verified operations above took effect. Any unverified or failed files were NOT created.")
        else:
            lines.append("### [COMPLETION_GUARD] Operation Not Completed\n")
            lines.append("The requested operation could not be completed as claimed. Security policy or execution checks prevented execution:\n")
            for f_rec in unresolved:
                reason = f_rec.reason_or_error or "Execution failed or was denied."
                target_str = f" (`{f_rec.target}`)" if f_rec.target else ""
                lines.append(f"- **`{f_rec.tool_name}`**{target_str}: {reason}")
            lines.append("\n> **Notice:** The requested file or system change was **NOT** completed on the host.")

        guarded_text = "\n".join(lines)
        claim_texts = [c[1] for c in false_claims]

        res = GuardResult(
            is_valid=False,
            guarded_text=guarded_text,
            false_claims_detected=claim_texts,
            unresolved_failures=unresolved,
            verified_successes=verified,
            correction_applied=True
        )
        return guarded_text, res
