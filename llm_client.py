"""
LLM Client Module using LiteLLM

Strictly respects mandatory constraints:
1. Uses LiteLLM library (`litellm.completion`).
2. Model name is strictly set to "llm".
3. Reads API Base URL and API Key from environment variables:
   - LITELLM_PROXY_API_BASE
   - LITELLM_PROXY_API_KEY
"""

import os
import sys
import ssl
import requests
import litellm
from config import MODEL_NAME, LITELLM_PROXY_API_BASE, LITELLM_PROXY_API_KEY

# Ensure SSL compatibility in corporate/proxy environments with self-signed certificate chains
ssl._create_default_https_context = ssl._create_unverified_context
_old_requests_send = requests.Session.send
requests.Session.send = lambda self, request, **kwargs: _old_requests_send(
    self, request, **{**kwargs, "verify": False}
)

# Turn off noisy telemetry/logging from LiteLLM
litellm.telemetry = False
litellm.suppress_debug_info = True



def call_llm(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """
    Sends a completion request using LiteLLM to the configured proxy.

    Args:
        messages: List of message objects [{'role': 'system'/'user', 'content': '...'}]
        temperature: Sampling temperature (default 0.2 for deterministic synthesis)

    Returns:
        String output content from the LLM.
    """
    # Fetch environment variables dynamically (fallback to config values if loaded)
    api_base = os.getenv("LITELLM_PROXY_API_BASE") or LITELLM_PROXY_API_BASE
    api_key = os.getenv("LITELLM_PROXY_API_KEY") or LITELLM_PROXY_API_KEY

    if not api_base or not api_key:
        print("\n❌ ERROR: Required environment variables are missing!")
        print("Please set the following environment variables before running:")
        print("  - LITELLM_PROXY_API_BASE (e.g. http://localhost:4000)")
        print("  - LITELLM_PROXY_API_KEY  (e.g. sk-123456)")
        print("\nOr configure them in a '.env' file in the project directory.\n")
        sys.exit(1)

    try:
        # LiteLLM completion API call strictly using model="llm"
        response = litellm.completion(
            model=MODEL_NAME,                 # Strictly "llm"
            custom_llm_provider="openai",     # Specify OpenAI-compatible proxy format for model="llm"
            api_base=api_base,                # LITELLM_PROXY_API_BASE
            api_key=api_key,                  # LITELLM_PROXY_API_KEY
            messages=messages,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        if content is None:
            return ""
        return content.strip()

    except Exception as e:
        print(f"\n❌ LiteLLM Proxy API Call Error: {e}")
        raise e
