class ModelManager:
    def __init__(self):
        self.text_model = "qwen2.5-0.5b-instruct-q4_k_m"
        
    def is_engine_running(self):
        return True
    
    def set_model(self, model):
        self.text_model = model

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
