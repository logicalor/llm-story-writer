"""Unit-test conftest: block live LLM calls.

Any unit test that reaches `tools._llm.generate_text` /
`generate_text_messages` (or the wiki `_chat_completion` shims, or any of the
re-exported `generate_text` symbols bound into other modules at import time)
will fail loudly with ``RuntimeError`` instead of silently hitting the local
LM Studio / Ollama endpoint.

Tests that legitimately exercise the real ``tools._llm`` helpers (with
``requests.post`` mocked at the HTTP layer) opt out by listing their
filename in ``_LLM_ALLOWED_FILES`` below.

Mock at the agent layer (e.g. ``patch("presentation.agents.<x>.render_recap_as_markdown",
return_value=...)``) when a test needs a controlled return value rather than
a hard failure.
"""

from __future__ import annotations

import pytest

# Test files that legitimately exercise tools._llm directly with HTTP mocked.
_LLM_ALLOWED_FILES: frozenset[str] = frozenset(
    {
        "test_llm_client.py",
    }
)


def _raise_live_llm_call(*_args: object, **_kwargs: object) -> str:
    raise RuntimeError(
        "Live LLM call attempted from a unit test. "
        "Patch the agent's render_recap_as_markdown / _call_llm shim, or "
        "patch tools._llm.generate_text(_messages) explicitly. See "
        "tests/unit/conftest.py for the block-list rationale."
    )


@pytest.fixture(autouse=True)
def _block_live_llm_calls(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Patch every known LLM entrypoint to raise.

    Applies to every unit test except those listed in ``_LLM_ALLOWED_FILES``.
    Tests that need a stubbed return value should layer their own
    ``monkeypatch.setattr`` / ``unittest.mock.patch`` *after* this fixture
    runs — patch ordering means later patches win.
    """
    if request.node.fspath.basename in _LLM_ALLOWED_FILES:
        return

    # Subprocess-based tool tests inherit os.environ, not parent-process
    # monkeypatches. Point children at a closed local port so leaked requests
    # fail quickly instead of reaching LM Studio's default 127.0.0.1:1234.
    monkeypatch.setenv("LLM_API_BASE", "http://127.0.0.1:1")

    # Core LLM helpers — late-import call sites (most src/tools modules do
    # ``from tools._llm import generate_text`` *inside* their _call_llm shim,
    # so patching the source module is enough for them).
    import tools._llm as _llm_mod

    monkeypatch.setattr(_llm_mod, "generate_text", _raise_live_llm_call)
    monkeypatch.setattr(_llm_mod, "generate_text_messages", _raise_live_llm_call)

    # Module-level imports that bound the name into the importing module's
    # namespace at import time — these must be patched on the *importing*
    # module, not the source.
    for module_path in (
        "tools.context_assembly",
        "tools.story_assembler",
        "tools.wiki_snapshot",
    ):
        try:
            module = __import__(module_path, fromlist=["generate_text"])
        except ImportError:
            continue
        if hasattr(module, "generate_text"):
            monkeypatch.setattr(
                module, "generate_text", _raise_live_llm_call, raising=True
            )

    # Wiki API path — `_chat_completion` wraps generate_text in
    # tools._wiki_api and tools.wiki_extract.
    for module_path in ("tools._wiki_api", "tools.wiki_extract"):
        try:
            module = __import__(module_path, fromlist=["_chat_completion"])
        except ImportError:
            continue
        if hasattr(module, "_chat_completion"):
            monkeypatch.setattr(
                module, "_chat_completion", _raise_live_llm_call, raising=True
            )
