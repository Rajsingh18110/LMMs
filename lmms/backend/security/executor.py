import subprocess
import os
from lmms.backend.security.models import ToolRequest, ToolResult
from lmms.backend.security.evidence import record_tool_evidence

class SecureExecutor:
    
    def execute(self, request: ToolRequest, permission_result, timeout: int = 120, print_callback=None) -> ToolResult:
        # We assume permission manager already vetted the request.
        if not permission_result.allowed:
            record_tool_evidence(request, permission_result, ToolResult("", "", 1, was_denied=True, deny_reason=permission_result.reason))
            return ToolResult("", "", 1, was_denied=True, deny_reason=permission_result.reason)
            
        # Sandbox logic for Terminal commands
        if request.tool_name == "terminal.run":
            cmd = request.kwargs.get("command", "")
            cwd = request.workspace if request.workspace and request.workspace != "None" else None
            
            try:
                import time
                import re
                import select
                process = subprocess.Popen(cmd, shell=True, executable='/bin/bash', cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                
                output = []
                start_time = time.time()
                timed_out = False
                lines_printed = 0
                max_print_lines = 30
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                
                while True:
                    if timeout and (time.time() - start_time) > timeout:
                        process.kill()
                        timed_out = True
                        timeout_msg = f"Command timed out after {timeout} seconds."
                        if print_callback:
                            print_callback(f"[red]{timeout_msg}[/red]")
                        break
                        
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if not ready:
                        if process.poll() is not None:
                            break
                        continue

                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                        
                    if line:
                        output.append(line)
                        if print_callback:
                            if lines_printed < max_print_lines:
                                # Strip raw ANSI sequences to prevent terminal corruption
                                safe_line = ansi_escape.sub('', line).rstrip()
                                # Escape Rich markup brackets
                                safe_line = safe_line.replace('[', '\\[').replace(']', '\\]')
                                
                                # Truncate very long lines to avoid screen freezing
                                if len(safe_line) > 200:
                                    safe_line = safe_line[:200] + "... [line truncated]"
                                    
                                if safe_line.strip(): # Only print if there's actual text left
                                    print_callback(f"[dim]{safe_line}[/dim]")
                                    lines_printed += 1
                            elif lines_printed == max_print_lines:
                                print_callback("[dim yellow]... (streaming output paused to prevent terminal freeze. Command is still running in background) ...[/dim yellow]")
                                lines_printed += 1
                            
                full_output = "".join(output)
                # Hard cap the AI context output too so we don't blow up the context window
                if len(full_output) > 50000:
                    full_output = full_output[:50000] + "\n... [OUTPUT TRUNCATED FOR CONTEXT]"
                
                if timed_out:
                    process.wait(timeout=1)
                    result = ToolResult(stdout=full_output, stderr=timeout_msg, exit_code=124)
                else:
                    result = ToolResult(stdout=full_output, stderr="", exit_code=process.returncode or 0)
                
            except KeyboardInterrupt:
                try:
                    process.kill()
                except:
                    pass
                result = ToolResult(stdout="".join(output), stderr="\n[Process interrupted by user (Ctrl+C)]", exit_code=130)
                
            except Exception as e:
                result = ToolResult(stdout="", stderr=str(e), exit_code=1)
                
            record_tool_evidence(request, permission_result, result)
            return result
            
        else:
            # We don't execute internal tools (browser, file) through subprocess. 
            # They are executed natively in main.py, but we record the evidence here.
            # So the caller (main.py) will do the execution and then record.
            return ToolResult("Internal tool execution delegated to main.py", "", 0)

executor = SecureExecutor()
