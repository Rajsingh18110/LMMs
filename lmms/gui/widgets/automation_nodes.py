"""
lmms.gui.widgets.automation_nodes - Node definitions for LMMs Automation Studio.
Implements n8n-style nodes for Triggers, AI Agents, Models, MCP Tools,
Code sandboxes, HTTP requests, and Flow Control.
"""

from __future__ import annotations

import lmms.gui.vendor_patches.nodegraph_pyqt6  # noqa: F401
from NodeGraphQt import BaseNode
from lmms.gui.branding import AutomationBranding


# ---------------------------------------------------------
# Triggers (Vibrant Orange #f97316)
# ---------------------------------------------------------
class ManualTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "Trigger manually"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("description", "Click 'Test workflow' to execute.")


class ChatMessageTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "When chat message received"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("listen_channel", "default")


class ScheduleTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "On a schedule"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("interval", "Every hour")
        self.create_property("cron_expression", "0 * * * *")


class WebhookTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "On webhook call"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("http_method", "POST")
        self.create_property("webhook_path", "/webhook/lmms-flow")


class FileWatchTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "On file changes"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("watch_directory", "./")
        self.create_property("event_type", "modified")


class AppEventTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "On app event"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)
        self.create_property("event_source", "engine")


class FormTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "On form submission"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)


class SubflowTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "When executed by another workflow"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)


class EvaluationTriggerNode(BaseNode):
    __identifier__ = "lmms.triggers"
    NODE_NAME = "When running evaluation"

    def __init__(self):
        super().__init__()
        self.set_color(249, 115, 22)
        self.add_output("output", display_name=False)


# ---------------------------------------------------------
# AI & Models (Purple #8b5cf6)
# ---------------------------------------------------------
class AIAgentNode(BaseNode):
    __identifier__ = "lmms.models"
    NODE_NAME = "AI Agent"

    def __init__(self):
        super().__init__()
        self.set_color(139, 92, 246)
        self.add_input("Input", display_name=True)
        self.add_input("Chat Model*", display_name=True)
        self.add_input("Memory", display_name=True)
        self.add_input("Tools", multi_input=True, display_name=True)
        self.add_output("Output", display_name=True)
        self.create_property("system_prompt", "You are an expert AI assistant that accomplishes workflows.")
        self.create_property("max_iterations", 10)


class ChatModelNode(BaseNode):
    __identifier__ = "lmms.models"
    NODE_NAME = "Chat Model"

    def __init__(self):
        super().__init__()
        self.set_color(139, 92, 246)
        self.add_input("Input", display_name=False)
        self.add_output("Model", display_name=True)
        self.create_property("provider", "local_engine")
        self.create_property("model_name", "qwen2.5-coder")
        self.create_property("temperature", 0.7)


# ---------------------------------------------------------
# Actions (Blue #3b82f6)
# ---------------------------------------------------------
class MCPToolNode(BaseNode):
    __identifier__ = "lmms.actions"
    NODE_NAME = "MCP Tool Call"

    def __init__(self):
        super().__init__()
        self.set_color(59, 130, 246)
        self.add_input("Input", display_name=False)
        self.add_output("Output", display_name=False)
        self.create_property("server_name", "filesystem")
        self.create_property("tool_name", "read_file")
        self.create_property("arguments_json", "{}")


class PythonCodeNode(BaseNode):
    __identifier__ = "lmms.actions"
    NODE_NAME = "Python Code"

    def __init__(self):
        super().__init__()
        self.set_color(59, 130, 246)
        self.add_input("Input", display_name=False)
        self.add_output("Output", display_name=False)
        self.create_property("script", "# Python transformation\nreturn items")


class HTTPRequestNode(BaseNode):
    __identifier__ = "lmms.actions"
    NODE_NAME = "HTTP Request"

    def __init__(self):
        super().__init__()
        self.set_color(59, 130, 246)
        self.add_input("Input", display_name=False)
        self.add_output("Output", display_name=False)
        self.create_property("method", "GET")
        self.create_property("url", "https://api.github.com")
        self.create_property("headers", "{}")


# ---------------------------------------------------------
# Logic (Cyan #06b6d4)
# ---------------------------------------------------------
class IfElseNode(BaseNode):
    __identifier__ = "lmms.logic"
    NODE_NAME = "If / Else"

    def __init__(self):
        super().__init__()
        self.set_color(6, 182, 212)
        self.add_input("Input", display_name=False)
        self.add_output("True", display_name=True)
        self.add_output("False", display_name=True)
        self.create_property("condition_field", "status")
        self.create_property("operator", "equals")
        self.create_property("value", "success")


ALL_AUTOMATION_NODES = [
    ManualTriggerNode,
    ChatMessageTriggerNode,
    ScheduleTriggerNode,
    WebhookTriggerNode,
    FileWatchTriggerNode,
    AppEventTriggerNode,
    FormTriggerNode,
    SubflowTriggerNode,
    EvaluationTriggerNode,
    AIAgentNode,
    ChatModelNode,
    MCPToolNode,
    PythonCodeNode,
    HTTPRequestNode,
    IfElseNode,
]


def register_all_nodes(graph):
    """Registers all custom LMMs automation nodes with a NodeGraph instance."""
    for node_cls in ALL_AUTOMATION_NODES:
        try:
            graph.register_node(node_cls)
        except Exception as e:
            import sys
            sys.stderr.write(f"[register_all_nodes] Error registering {node_cls}: {e}\n")
