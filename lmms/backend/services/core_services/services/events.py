import threading
from typing import Callable, Dict, List, Any

class EventManager:
    """
    Pub/Sub Event Bus for LMMs Operating System.
    Decouples core systems (Registry, Providers, CLI, GUI, Agents).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventManager, cls).__new__(cls)
                cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, event_name: str, callback: Callable[[Any], None]):
        """Subscribe to an event."""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]):
        """Unsubscribe from an event."""
        with self._lock:
            if event_name in self._subscribers and callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, data: Any = None):
        """Publish an event to all subscribers."""
        with self._lock:
            callbacks = self._subscribers.get(event_name, []).copy()
        
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                # In a robust system, we would log this to a central logger
                print(f"[EventManager] Error in callback for event '{event_name}': {e}")

# Global singleton instance
event_bus = EventManager()
