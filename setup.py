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
    version="2.0.4",
    author="MarkanM Team (Developer: Raj Singh)",
    description="Local Multi-Model AI System — open style agent",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        # Core CLI & Agent
        "ollama", "rich", "duckduckgo-search", "playwright",
        "requests", "click", "prompt_toolkit", "openai",
        "anthropic", "pathspec", "plotext", "textual",
        "huggingface_hub", "watchdog", "transformers", "airllm",

        # GUI (PyQt6)
        "PyQt6", "PyQt6-Qt6", "PyQt6-sip", "qasync", "PyQt6-WebEngine", "python-lsp-server",

        # Backend API & Server
        "fastapi", "uvicorn[standard]", "httpx[http2]",
        "websockets", "pydantic", "nest_asyncio", "psutil",

        # AI / ML & Inference
        "sentence-transformers", "numpy",

        # Markdown & Text Processing
        "markdown",

        # Database
        "sqlite-vec",
        
        # Utilities
        "keyring", "debugpy>=1.8.0",
    ],
    py_modules=["launcher", "gui"],
    entry_points={
        "console_scripts": [
            "LMMs=launcher:main",
            "lmms=launcher:main",
            "LMMS=launcher:main",
            "lmms-gui=gui:main",
            "LMMs-uninstall=launcher:uninstall_main",
            "lmms-uninstall=launcher:uninstall_main",
        ],
    },
    cmdclass={
        'build_py': BuildPyCommand,
    },
    python_requires=">=3.10",
)
