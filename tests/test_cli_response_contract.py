from lmms.backend.main import extract_active_model_from_stats, should_force_tool_mode


def test_extract_active_model_from_engine_stats():
    assert extract_active_model_from_stats({"loaded_models": ["model-a", "model-b"]}) == "model-a"
    assert extract_active_model_from_stats({"models": {"model-b": {}}}) == "model-b"
    assert extract_active_model_from_stats({}) is None


def test_default_chat_should_not_force_tool_mode():
    assert should_force_tool_mode("hello") is False
    assert should_force_tool_mode("hi there") is False
    assert should_force_tool_mode("what is the meaning of life?") is False


def test_explicit_agent_tasks_should_force_tool_mode():
    assert should_force_tool_mode("use browser.open_url to inspect the site") is True
    assert should_force_tool_mode("use browser.crawl_url to read this site") is True
    assert should_force_tool_mode("crawl4ai this URL and summarize it") is True
    assert should_force_tool_mode("search the web for latest AI news") is True
    assert should_force_tool_mode("read /etc/hosts and summarize it") is True


def test_runtime_strips_stray_reasoning_when_thinking_disabled():
    from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime

    runtime = LlamaCppRuntime()
    text = 'We need to answer only OK.\n</think>\nOK'

    assert runtime._strip_hidden_reasoning(text) == "OK"


def test_response_cleaner_strips_plain_english_reasoning_leak():
    from lmms.engine.response_cleaner import strip_hidden_reasoning

    text = (
        'The user is asking "hello" again. According to the system rules, '
        "I should answer naturally without introducing myself. "
        "The previous response was a placeholder. Now I need to respond appropriately.\n\n"
        "Since this is a normal conversational request, I'll just say hello back. "
        "No tool usage needed. Hello!"
    )

    assert strip_hidden_reasoning(text) == "Hello!"


def test_response_cleaner_keeps_valid_short_answer():
    from lmms.engine.response_cleaner import strip_hidden_reasoning

    assert strip_hidden_reasoning("I need more information.") == "I need more information."


def test_qwen3_models_use_qwen_chat_format_fallback():
    from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime

    runtime = LlamaCppRuntime()

    assert runtime._detect_chat_format("/tmp/Qwen3-8B-Q4_K_M.gguf") == "qwen"
    assert runtime._detect_chat_format("/tmp/qwen2.5-1.5b-instruct-q4_k_m.gguf") == "qwen"
    assert runtime._detect_chat_format("/tmp/Llama-3.1-8B-Instruct.gguf") == "llama-2"
    assert runtime._detect_chat_format("/tmp/custom-model.gguf") is None
