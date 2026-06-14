from setuptools import setup, find_packages

setup(
    name="LMMs",
    version="2.0.0",
    author="MarkanM Team (Developer: Raj Singh)",
    description="Local Multi-Model AI System — open style agent",
    packages=find_packages(),
    install_requires=[
        "ollama", "rich", "duckduckgo-search", "playwright",
        "requests", "click", "prompt_toolkit", "openai",
        "anthropic", "pathspec", "plotext", "textual",
        "huggingface_hub", "watchdog", "transformers", "airllm",
    ],
    entry_points={
        "console_scripts": [
            "LMMs=main:main",
        ],
    },
    python_requires=">=3.10",
)
