import re

with open("lmms/engine/runtimes/llama_cpp.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_stream_response = False
for i, line in enumerate(lines):
    if line.startswith('            def stream_response():'):
        new_lines.append(line)
        new_lines.append('                self._global_lock.acquire()\n')
        new_lines.append('                try:\n')
        in_stream_response = True
        continue
        
    if in_stream_response:
        if line.strip() == 'return stream_response()':
            in_stream_response = False
            new_lines.append('                finally:\n')
            new_lines.append('                    self._global_lock.release()\n')
            new_lines.append(line)
            continue
            
        # Inside stream_response, indent everything by 4 spaces
        # EXCEPT we need to remove the old `with self._global_lock:` 
        if line.strip() == 'with self._global_lock:':
            continue
            
        if line.startswith('                    response_generator = active_model.create_chat_completion('):
            new_lines.append(line)
            continue
            
        # The while loop had `with self._global_lock:` inside it.
        # We removed it, so we need to dedent its body by 4 spaces!
        
        # Actually, let's just write the stream_response block manually and insert it!
