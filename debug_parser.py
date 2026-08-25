from lmms.backend.services.chat_service import ChatService
class DummyAgentManager:
    async def execute_task(self, context):
        yield ""

service = ChatService(DummyAgentManager())
service.active_message_id = "1"
events, buf, think, syslog = service._parse_buffer("</think>I'm not sure", False, False)
for e in events: print(e.type, e.content)
print(f"buf: '{buf}', think: {think}")
