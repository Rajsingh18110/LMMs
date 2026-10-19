class ModelManager:
    def __init__(self):
        self.text_model = "qwen2.5-0.5b-instruct-q4_k_m"
        self.vision_model = "llava"
        self.critic_model = "gemma-2b"
        
    def is_engine_running(self):
        return True
    
    def set_model(self, model):
        self.text_model = model

    def unload_model(self, model_name=None):
        """Unload a model from memory/VRAM."""
        return True

    def cloud_chat(self, connector_name: str, messages: list) -> str:
        """Execute chat completion via cloud connector."""
        return ""

    def list_connectors(self):
        return []

    def get_model_status_table(self):
        return ""

    def download_huggingface_model(self, query):
        pass

    def add_connector(self, *args, **kwargs):
        pass

    def remove_connector(self, *args, **kwargs):
        return True
