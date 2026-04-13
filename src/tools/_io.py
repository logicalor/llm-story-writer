"""Shared I/O utilities for tool scripts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    fd_closed = False
    try:
        os.write(fd, content.encode())
        os.close(fd)
        fd_closed = True
        os.replace(tmp, str(path))
    except BaseException:
        if not fd_closed:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
