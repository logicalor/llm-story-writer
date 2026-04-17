from __future__ import annotations

import os

import pytest
import requests


@pytest.fixture(scope="session")
def llm_available() -> str:
    base = os.environ.get("LLM_API_BASE", "http://localhost:11434/v1").rstrip("/")

    try:
        response = requests.get(f"{base}/models", timeout=10)
    except requests.RequestException:
        pytest.skip("LLM service not available — skipping integration tests")

    if response.status_code != 200:
        pytest.skip("LLM service not available — skipping integration tests")

    return base
