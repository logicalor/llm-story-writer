"""Verification tests for shared wiki utilities (src/tools/_wiki.py).

Covers _validate_slug path-traversal rejection (Issue #57).
"""

from __future__ import annotations

import pytest

from src.tools._wiki import _validate_slug


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

    def test_validate_slug_accepts_valid_slug(self) -> None:
        # Should not raise or exit
        _validate_slug("valid-slug")
