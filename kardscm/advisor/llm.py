"""LLM provider dispatch and thin SDK wrappers."""

from __future__ import annotations

import os

from kardscm.config import AdvisorConfig


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> str:
    """Call OpenAI API."""
    import openai

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


def _call_anthropic(system_prompt: str, user_prompt: str, model: str) -> str:
    """Call Anthropic API."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return str(response.content[0].text)


def _call_google(system_prompt: str, user_prompt: str, model: str) -> str:
    """Call Google Generative AI API."""
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
    )
    response = gen_model.generate_content(user_prompt)
    return response.text or ""


_PROVIDERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "google": _call_google,
}


def get_llm_response(system_prompt: str, user_prompt: str, config: AdvisorConfig) -> str:
    """Dispatch to the configured LLM provider and return the response.

    Args:
        system_prompt: System/instruction prompt.
        user_prompt: User message with analysis context.
        config: Advisor configuration with provider, model, depth.

    Returns:
        LLM response text.

    Raises:
        ValueError: If provider is not supported.
    """
    handler = _PROVIDERS.get(config.provider)
    if handler is None:
        raise ValueError(
            f"Unsupported LLM provider: '{config.provider}'. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}"
        )
    return handler(system_prompt, user_prompt, config.model)
