from PyQt6.QtCore import QObject, pyqtSignal

class OutputChannelRegistry(QObject):
    _instance = None
    
    # Signal emitted when a new message is appended: channel_name, message
    message_appended = pyqtSignal(str, str)
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        super().__init__()
        self._channels = {}
        
    def append(self, channel_name: str, message: str):
        if channel_name not in self._channels:
            self._channels[channel_name] = []
            
        self._channels[channel_name].append(message)
        self.message_appended.emit(channel_name, message)
        
    def get_channels(self):
        return list(self._channels.keys())
        
    def get_channel_content(self, channel_name: str):
        return "\n".join(self._channels.get(channel_name, []))
