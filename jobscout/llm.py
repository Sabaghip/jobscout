from __future__ import annotations

from jobscout.config import llm_provider


def get_llm():
    provider = llm_provider()
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model="claude-sonnet-5", temperature=0)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'openai' or 'anthropic')")
