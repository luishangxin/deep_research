"""
LocalSandboxProvider — thread-isolated local filesystem sandbox.

Each thread (conversation session) gets its own working directory under
/tmp/deerflow_sandbox/{thread_id}/, ensuring file operations are isolated
between concurrent sessions.

Thread isolation is achieved via threading.local() which stores the current
provider instance, preventing cross-talk between concurrent requests.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import threading
from pathlib import Path

from src.sandbox.base import SandboxProvider

# Thread-local storage for sandbox instances
_thread_local = threading.local()

# Base directory for all sandboxes
SANDBOX_BASE = Path(os.environ.get("SANDBOX_BASE", "/tmp/deerflow_sandbox"))


class LocalSandboxProvider(SandboxProvider):
    """
    Sandbox that executes commands and file operations in a thread-specific
    local directory under SANDBOX_BASE/{thread_id}/.

    Args:
        thread_id: A unique identifier for the current session/thread.
                   Defaults to the OS thread ID.
    """

    def __init__(self, thread_id: str | None = None) -> None:
        self._thread_id = thread_id or str(threading.get_ident())
        self._workdir = SANDBOX_BASE / self._thread_id
        self._workdir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_workdir(self) -> str:
        return str(self._workdir)

    def execute_command(self, cmd: str, timeout: int = 30) -> str:
        """Run a shell command inside the sandbox workdir."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self._workdir),
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            return output.strip()
        except subprocess.TimeoutExpired:
            return f"[error] Command timed out after {timeout}s: {cmd}"
        except Exception as exc:
            return f"[error] {exc}"

    def read_file(self, path: str) -> str:
        """Read a file from the sandbox, resolving path relative to workdir."""
        resolved = self._resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"No such file: {path} (resolved: {resolved})")
        return resolved.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> None:
        """Write content to a file in the sandbox."""
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

    def list_dir(self, path: str = ".") -> list[str]:
        """List entries in a sandbox directory."""
        resolved = self._resolve(path)
        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return sorted(p.name for p in resolved.iterdir())

    # ------------------------------------------------------------------
    # Class-level helpers for thread-local access
    # ------------------------------------------------------------------

    @classmethod
    def get_current(cls) -> "LocalSandboxProvider":
        """
        Return the LocalSandboxProvider for the current thread.
        Creates one lazily if it doesn't exist yet.
        """
        if not hasattr(_thread_local, "sandbox"):
            _thread_local.sandbox = cls()
        return _thread_local.sandbox

    @classmethod
    def set_current(cls, provider: "LocalSandboxProvider") -> None:
        """Attach a specific provider to the current thread."""
        _thread_local.sandbox = provider

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        """
        Resolve a user-supplied path against the sandbox workdir.

        Prevents path traversal attacks by ensuring the final path is
        always underneath self._workdir.
        """
        resolved = (self._workdir / path).resolve()
        # Security: block path traversal
        try:
            resolved.relative_to(self._workdir.resolve())
        except ValueError:
            raise PermissionError(
                f"Path traversal detected: '{path}' escapes sandbox workdir"
            )
        return resolved
