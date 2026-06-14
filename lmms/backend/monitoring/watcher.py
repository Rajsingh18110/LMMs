import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class GGUFHandler(FileSystemEventHandler):
    def __init__(self, watch_dir):
        self.watch_dir = watch_dir

    def on_created(self, event):
        if event.is_directory:
            return
            
        filepath = event.src_path
        if filepath.endswith(".gguf"):
            # Wait a moment for file copy to finish
            time.sleep(2)
            
            filename = os.path.basename(filepath)
            model_name = filename.replace(".gguf", "").lower()
            modelfile_path = os.path.join(self.watch_dir, f"Modelfile_{model_name}")
            
            try:
                # Generate Modelfile
                print(f"\n[Watchdog] Detected new model {filename}! Ready to use.")
                print(f"[Watchdog] Successfully imported {model_name}. Use /model {model_name} to use it.")
            except Exception as e:
                print(f"\n[Watchdog] Failed to import {filename}: {e}")

def start_watcher():
    watch_dir = os.path.expanduser("~/.lmms/models/")
    os.makedirs(watch_dir, exist_ok=True)
    
    # Do an initial scan for orphaned .gguf files
    for f in os.listdir(watch_dir):
        if f.endswith(".gguf"):
            model_name = f.replace(".gguf", "").lower()
            # If Modelfile doesn't exist, we assume it hasn't been imported
            modelfile_path = os.path.join(watch_dir, f"Modelfile_{model_name}")
            if not os.path.exists(modelfile_path):
                print(f"\n[Watchdog] Modified model {f}! Ready to use.")
    
    event_handler = GGUFHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=False)
    observer.start()
    return observer
