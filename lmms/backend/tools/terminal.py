import subprocess

BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "chmod 777 /",
    ":(){ :|:& };:",
    "fork bomb",
]


class TerminalTool:
    def run(self, command: str, require_confirm=False, cwd=None) -> str:
        # Check if dangerous
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return f"BLOCKED: Dangerous command '{blocked}' detected."

        # Confirm if needed
        if require_confirm:
            confirm = input(f"Run: `{command}`? (y/n): ")
            if confirm.lower() != "y":
                return "Command execution cancelled by user."

        if hasattr(self, "agent") and self.agent:
            self.agent.push_action({
                "type": "terminal_command",
                "command": command
            })

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30, cwd=cwd
            )
            output = result.stdout + result.stderr
            if not output:
                return "Command executed successfully with no output."
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"
