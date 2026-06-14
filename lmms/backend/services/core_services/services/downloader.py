import os
import requests
import time
import threading

class DownloadManager:
    """
    Unified downloading manager for CLI and GUI.
    Handles background downloads, progress tracking, and registry updating.
    """
    def __init__(self, registry):
        self.registry = registry
        self.active_downloads = {}

    def download_model(self, repo_id: str, filename: str, provider="Hugging Face", progress_callback=None, complete_callback=None, error_callback=None):
        """Starts a download in a background thread."""
        thread_id = f"{repo_id}/{filename}"
        if thread_id in self.active_downloads:
            if error_callback:
                error_callback("Download already in progress.")
            return

        def _download_task():
            try:
                url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                # Standardized save path
                save_path = os.path.expanduser(f"~/.lmms/models/{repo_id.replace('/', '_')}/{filename}")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                downloaded_size = 0
                start_time = time.time()
                last_time = start_time
                last_size = 0
                
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=65536):
                        if not chunk: break
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        now = time.time()
                        if now - last_time > 0.5:
                            speed = (downloaded_size - last_size) / (now - last_time)
                            pct = int((downloaded_size / total_size) * 100) if total_size > 0 else 0
                            
                            if speed > 1024*1024: speed_str = f"{speed/(1024*1024):.1f} MB/s"
                            else: speed_str = f"{speed/1024:.1f} KB/s"
                            
                            if downloaded_size > 1024*1024*1024: dl_str = f"{downloaded_size/(1024*1024*1024):.1f} GB"
                            else: dl_str = f"{downloaded_size/(1024*1024):.1f} MB"
                            
                            if progress_callback:
                                progress_callback(pct, speed_str, dl_str)
                            
                            last_time = now
                            last_size = downloaded_size

                # Register the model
                model_id = f"{repo_id}/{filename}"
                format_ext = "GGUF" if filename.endswith(".gguf") else "Safetensors"
                self.registry.add_model(
                    model_id=model_id,
                    provider=provider,
                    path=save_path,
                    format=format_ext,
                    size=total_size,
                    source="Downloaded",
                    capabilities=["Text"]
                )
                
                from lmms.backend.services.core_services.events import event_bus
                event_bus.publish("ModelDownloaded", {"model_id": model_id, "path": save_path})
                
                if complete_callback:
                    complete_callback(save_path)
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
            finally:
                self.active_downloads.pop(thread_id, None)

        thread = threading.Thread(target=_download_task)
        self.active_downloads[thread_id] = thread
        thread.start()
