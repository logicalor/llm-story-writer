"""Verification tests for shared wiki utilities (src/tools/_wiki.py).

Covers _validate_slug path-traversal rejection (Issue #57) and
_validate_glob_pattern slash/traversal rejection (Issue #59).
"""

from __future__ import annotations

import pytest

from src.tools._wiki import _validate_glob_pattern, _validate_slug


class TestValidateSlug:
    """Tests for _validate_slug path-traversal guard."""

    def test_validate_slug_rejects_backslash(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_slug("some\\slug")
        assert exc_info.value.code == 1

    def test_validate_slug_rejects_dotdot(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_slug("..secret")
        assert exc_info.value.code == 1

    def test_validate_slug_rejects_forward_slash(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_slug("path/slug")
        assert exc_info.value.code == 1

    def test_validate_slug_rejects_windows_traversal(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_slug("..\\..\\etc\\passwd")
        assert exc_info.value.code == 1

    def test_validate_slug_accepts_valid_slug(self) -> None:
        # Should not raise or exit
        _validate_slug("valid-slug")


class TestValidateGlobPattern:
    """Tests for _validate_glob_pattern path-traversal and slash guard."""

    def test_validate_glob_pattern_rejects_backslash(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_glob_pattern("some\\pattern")
        assert exc_info.value.code == 1

    def test_validate_glob_pattern_rejects_forward_slash(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_glob_pattern("path/pattern")
        assert exc_info.value.code == 1

    def test_validate_glob_pattern_rejects_dotdot(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_glob_pattern("..secret")
        assert exc_info.value.code == 1

    def test_validate_glob_pattern_accepts_valid_pattern(self) -> None:
        # Should not raise or exit
        _validate_glob_pattern("*.md")
