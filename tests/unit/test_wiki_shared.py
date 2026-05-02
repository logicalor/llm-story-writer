"""Verification tests for shared wiki utilities (src/tools/_wiki.py).

Covers _validate_slug path-traversal rejection (Issue #57) and
_validate_glob_pattern slash/traversal rejection (Issue #59).

Behaviour change: validators now raise ValueError rather than calling
sys.exit, so the orchestrator can catch invalid input and roll back
without terminating the long-running pipeline process.
"""

from __future__ import annotations

import pytest

from src.tools._wiki import _validate_glob_pattern, _validate_slug


class TestValidateSlug:
    """Tests for _validate_slug path-traversal guard."""

    def test_validate_slug_rejects_backslash(self) -> None:
        with pytest.raises(ValueError):
            _validate_slug("some\\slug")

    def test_validate_slug_rejects_dotdot(self) -> None:
        with pytest.raises(ValueError):
            _validate_slug("..secret")

    def test_validate_slug_rejects_forward_slash(self) -> None:
        with pytest.raises(ValueError):
            _validate_slug("path/slug")

    def test_validate_slug_rejects_windows_traversal(self) -> None:
        with pytest.raises(ValueError):
            _validate_slug("..\\..\\etc\\passwd")

    def test_validate_slug_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            _validate_slug("")

    def test_validate_slug_accepts_valid_slug(self) -> None:
        _validate_slug("valid-slug")


class TestValidateGlobPattern:
    """Tests for _validate_glob_pattern path-traversal and slash guard."""

    def test_validate_glob_pattern_rejects_backslash(self) -> None:
        with pytest.raises(ValueError):
            _validate_glob_pattern("some\\pattern")

    def test_validate_glob_pattern_rejects_forward_slash(self) -> None:
        with pytest.raises(ValueError):
            _validate_glob_pattern("path/pattern")

    def test_validate_glob_pattern_rejects_dotdot(self) -> None:
        with pytest.raises(ValueError):
            _validate_glob_pattern("..secret")

    def test_validate_glob_pattern_accepts_valid_pattern(self) -> None:
        _validate_glob_pattern("*.md")
