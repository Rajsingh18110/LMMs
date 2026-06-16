from PyQt6.QtCore import QThread, pyqtSignal
from lmms.backend.agents.core_agents.agents.manager import AgentManager
from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.tasks.core_tasks.task import Task
import asyncio

class ChatService(QThread):
    chunk_received = pyqtSignal(str)
    response_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, agent_manager: AgentManager):
        super().__init__()
        self.agent_manager = agent_manager
        self.prompt = ""
        self.image_path = None

    def start_chat(self, prompt: str, image_path: str = None):
        self.prompt = prompt
        self.image_path = image_path
        self.start()

    def run(self):
        try:
            # Construct a basic task context
            context = ExecutionContext(
                task=Task(
                    id="chat-1", 
                    title="User Prompt",
                    description=self.prompt
                ),
                memory=[{"role": "user", "content": self.prompt}]
            )
            
            async def run_async():
                full_text = ""
                async for chunk in self.agent_manager.execute_task(context):
                    full_text += chunk
                    self.chunk_received.emit(full_text)
                    
            asyncio.run(run_async())
            self.response_finished.emit("Done")
        except Exception as e:
            self.error_occurred.emit(str(e))
