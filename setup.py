from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
import compileall
import os

class BuildPyCommand(build_py):
    """Custom build command to compile source code to bytecode."""
    def run(self):
        super().run()
        # Compile to bytecode with legacy=True so .pyc replaces .py directly
        compileall.compile_dir(self.build_lib, force=True, legacy=True, quiet=1)
        # Remove original .py files
        for root, dirs, files in os.walk(self.build_lib):
            for file in files:
                if file.endswith('.py'):
                    os.remove(os.path.join(root, file))

setup(
    name="LMMs",
    version="2.0.0",
    author="MarkanM Team (Developer: Raj Singh)",
    description="Local Multi-Model AI System — open style agent",
    packages=find_packages(),
    install_requires=[
        # Core CLI & Agent
        "ollama", "rich", "duckduckgo-search", "playwright",
        "requests", "click", "prompt_toolkit", "openai",
        "anthropic", "pathspec", "plotext", "textual",
        "huggingface_hub", "watchdog", "transformers", "airllm",

        # GUI (PyQt6)
        "PyQt6", "PyQt6-Qt6", "PyQt6-sip", "qasync",

        # Backend API & Server
        "fastapi", "uvicorn[standard]", "httpx[http2]",
        "websockets", "pydantic", "nest_asyncio", "psutil",

        # AI / ML & Inference
        "sentence-transformers", "numpy",

        # Markdown & Text Processing
        "markdown",

        # Database
        "sqlite-vec",
    ],
    entry_points={
        "console_scripts": [
            "LMMs=main:main",
            "lmms-gui=lmms_gui_entry:main",
        ],
    },
    cmdclass={
        'build_py': BuildPyCommand,
    },
    python_requires=">=3.10",
)
