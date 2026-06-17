from __future__ import annotations

import json

try:
    import requests
except ImportError:  # pragma: no cover - lightweight runtimes may not have requests installed
    requests = None

from config import AIML_API_URL, get_secret


def call_aiml_api(system_prompt: str, user_prompt: str, model_name: str) -> str:
    """Call the AI/ML API and return the assistant text or a helpful error string."""
    if requests is None:
        return "Error: requests package is unavailable in this runtime."
    api_key = get_secret("AIML_API_KEY")
    if not api_key:
        return (
            "Error: AIML_API_KEY is missing. Add it to your .env file or Streamlit secrets "
            "before running AI-powered agents."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    try:
        response = requests.post(
            AIML_API_URL,
            headers=headers,
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        details = exc.response.text[:500] if exc.response is not None else str(exc)
        return f"HTTP error while calling AI/ML API: {details}"
    except requests.exceptions.RequestException as exc:
        return f"Request error while calling AI/ML API: {exc}"

    try:
        data = response.json()
    except ValueError:
        return "Error: AI/ML API returned a non-JSON response."

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError):
        return (
            "Error: Unexpected AI/ML API response format. "
            f"Received: {json.dumps(data)[:500]}"
        )
