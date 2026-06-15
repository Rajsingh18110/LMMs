import os
import sys

import warnings
from rich.console import Console

console = Console()

class UniversalPyTorchRuntime:
    def __init__(self):
        self._pipe = None
        self._model_id = None
        self.pipeline_tag = None
        self.autoplay_audio = False
        self._kokoro_pipeline = None

    def load_model(self, model_id: str) -> bool:
        self._model_id = model_id
        
        # Check if it's Kokoro
        if "kokoro" in model_id.lower():
            try:
                from kokoro import KPipeline  # type: ignore
                console.print(f"[dim]Loading dedicated Kokoro TTS Pipeline for {model_id}...[/dim]")
                # Load Kokoro pipeline (American English default for now)
                self._kokoro_pipeline = KPipeline(lang_code='a') 
                console.print(f"[bold green]Successfully loaded {model_id} via Kokoro Dedicated Pipeline[/bold green]")
                return True
            except ImportError:
                console.print(f"[red]Kokoro package missing! Please run: {sys.executable} -m pip install kokoro soundfile --break-system-packages[/red]")
                return False
            except Exception as e:
                console.print(f"[red]Failed to load Kokoro model: {e}[/red]")
                return False

        # Fallback to Universal Hugging Face Pipeline
        try:
            # Inject beautiful circular progress bar
            import sys
            import tqdm
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            class RichTqdm(tqdm.tqdm):
                def __init__(self, *args, **kwargs):
                    self.rich_progress = Progress(
                        SpinnerColumn("circle"),
                        TextColumn("[cyan]{task.description}"),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        transient=True
                    )
                    self.total_val = kwargs.get("total", 100)
                    desc = kwargs.get("desc", "Downloading Neural Weights...")
                    self.rich_progress.start()
                    self.task_id = self.rich_progress.add_task(desc, total=self.total_val)
                    super().__init__(*args, **kwargs, disable=True)
                    
                def update(self, n=1):
                    self.rich_progress.update(self.task_id, advance=n)
                    super().update(n)
                    
                def close(self):
                    self.rich_progress.stop()
                    super().close()
            
            tqdm.tqdm = RichTqdm
            tqdm.auto = type("auto", (), {"tqdm": RichTqdm})
            sys.modules["tqdm"] = tqdm
            sys.modules["tqdm.auto"] = tqdm.auto
            
            try:
                from huggingface_hub.utils import _tqdm
                _tqdm.tqdm = RichTqdm
                import transformers.utils.logging as hf_logging
                hf_logging.disable_progress_bar()
            except: pass
            
            from transformers import pipeline
            import logging
            logging.getLogger("transformers").setLevel(logging.ERROR)
            warnings.filterwarnings("ignore")
            
            console.print(f"[dim]Loading Universal PyTorch Pipeline for: {model_id} (Task: {self.pipeline_tag})...[/dim]")
            
            # Use device_map="auto" to handle multi-GPU or CPU automatically
            self._pipe = pipeline(model=model_id, device_map="auto")
            console.print(f"[bold green]Successfully loaded {model_id} via Universal Pipeline (Task: {self._pipe.task})[/bold green]")
            return True
        except Exception as e:
            console.print(f"[red]Universal PyTorch Engine failed to load {model_id}: {e}[/red]")
            return False

    def generate(self, params: dict, stream: bool = True):
        messages = params.get("messages", [])
        
        # Determine the user's latest text prompt
        user_text = ""
        user_image = None
        user_audio = None
        if messages and isinstance(messages[-1].get("content"), list):
            for item in messages[-1]["content"]:
                if item["type"] == "text":
                    user_text = item["text"]
                elif item["type"] == "image_url":
                    user_image = item["image_url"]["url"]
                elif item["type"] == "audio_url":
                    user_audio = item["audio_url"]["url"]
        elif messages:
            user_text = messages[-1].get("content", "")

        # Kokoro Dedicated Handling
        if self._kokoro_pipeline:
            try:
                import soundfile as sf  # type: ignore
                console.print("\n[dim magenta]🎙️ Generating Audio (Kokoro)...[/dim magenta]")
                # Generate audio
                generator = self._kokoro_pipeline(
                    user_text, voice='af_heart', # Default voice
                    speed=1, split_pattern=r'\n+'
                )
                
                audio_chunks = []
                sample_rate = 24000
                for gs, ps, audio in generator:
                    audio_chunks.append(audio)
                    
                if not audio_chunks:
                    yield {"message": {"content": "Error: Failed to generate audio."}}
                    return
                
                import numpy as np
                final_audio = np.concatenate(audio_chunks)
                import os
                out_path = "/tmp/lmms_audio_response.wav"
                sf.write(out_path, final_audio, sample_rate)
                
                msg = "[Playing generated audio...]\n"
                
                import subprocess
                import threading
                def play_audio():
                    try:
                        if subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
                            subprocess.run(["aplay", "-q", out_path])
                        elif subprocess.run(["which", "ffplay"], capture_output=True).returncode == 0:
                            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", out_path])
                    except: pass
                threading.Thread(target=play_audio, daemon=True).start()
                    
                yield {"message": {"content": msg}}
                return
            except Exception as e:
                yield {"message": {"content": f"Kokoro Generation Error: {e}"}}
                return

        # Universal Pipeline Handling
        if not self._pipe:
            yield {"message": {"content": "Error: No model loaded in Universal Engine."}}
            return
            
        task = self._pipe.task
        try:
            if task in ["text-generation", "text2text-generation"]:
                # Simple text generation via pipeline
                # Convert messages to a single prompt string if model doesn't support chat templates natively
                prompt = user_text
                if hasattr(self._pipe.tokenizer, "apply_chat_template"):
                    prompt = self._pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    
                res = self._pipe(prompt, max_new_tokens=512, return_full_text=False)
                output_text = res[0]["generated_text"] if res else ""
                yield {"message": {"content": output_text}}
                
            elif task == "image-to-text" or task == "visual-question-answering":
                if not user_image:
                    yield {"message": {"content": "Error: This model requires an image, but none was provided. Use /image or drag and drop."}}
                    return
                
                # Extract base64 image and convert to PIL
                import base64
                from io import BytesIO
                from PIL import Image
                
                b64_data = user_image.split("base64,")[-1]
                img_data = base64.b64decode(b64_data)
                pil_img = Image.open(BytesIO(img_data)).convert("RGB")
                
                console.print("\n[dim magenta]👁️ Processing Image...[/dim magenta]")
                # The pipeline generally accepts (image, prompt) or just image depending on the specific VLM
                # We try passing both
                try:
                    res = self._pipe(pil_img, prompt=user_text)
                except:
                    # Fallback to standard
                    res = self._pipe(images=pil_img, prompt=user_text)
                    
                output_text = res[0].get("generated_text", str(res))
                yield {"message": {"content": output_text}}
                
            elif task == "text-to-speech":
                # Generic TTS fallback for non-Kokoro models
                import soundfile as sf  # type: ignore
                console.print("\n[dim magenta]🎙️ Generating Audio...[/dim magenta]")
                res = self._pipe(user_text)
                
                out_path = "/tmp/lmms_audio_response.wav"
                sf.write(out_path, res["audio"][0], res["sampling_rate"])
                
                msg = "[Playing generated audio...]\n"
                import subprocess
                import threading
                def play_audio():
                    try:
                        if subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
                            subprocess.run(["aplay", "-q", out_path])
                    except: pass
                threading.Thread(target=play_audio, daemon=True).start()
                
                yield {"message": {"content": msg}}
                
            elif task == "automatic-speech-recognition":
                if not user_audio:
                    yield {"message": {"content": "Error: This model requires an audio file. Please provide an audio file path or use the client microphone recording feature."}}
                    return
                    
                import base64
                import io
                import soundfile as sf  # type: ignore
                
                console.print("\n[dim magenta]🎧 Transcribing Audio...[/dim magenta]")
                b64_data = user_audio.split("base64,")[-1]
                audio_bytes = base64.b64decode(b64_data)
                
                # Convert the audio to numpy array
                data, samplerate = sf.read(io.BytesIO(audio_bytes))
                
                # Resample to 16kHz if necessary (Whisper expects 16k)
                if samplerate != 16000:
                    import scipy.signal
                    num_samples = int(len(data) * 16000 / samplerate)
                    data = scipy.signal.resample(data, num_samples)
                    samplerate = 16000
                
                res = self._pipe({"sampling_rate": samplerate, "raw": data})
                output_text = res.get("text", str(res))
                
                yield {"message": {"content": output_text}}
                
            else:
                yield {"message": {"content": f"[Unsupported Universal Task: {task}. We are constantly adding new modalities!] "}}
        except Exception as e:
            yield {"message": {"content": f"\n[Universal Engine Error: {e}]\n"}}
