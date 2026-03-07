"""
Abstract SandboxProvider — base class defining the sandbox contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class SandboxProvider(ABC):
    """
    Abstract interface for a sandboxed execution environment.

    All concrete implementations must provide:
      - execute_command: run a shell command and return its stdout/stderr
      - read_file:       read a file path within the sandbox
      - write_file:      write content to a file path within the sandbox
      - list_dir:        list directory contents within the sandbox
    """

    @abstractmethod
    def execute_command(self, cmd: str, timeout: int = 30) -> str:
        """
        Execute a shell command in the sandbox.

        Args:
            cmd: Shell command string.
            timeout: Max seconds to wait.

        Returns:
            Combined stdout + stderr as a string.
        """
        ...

    @abstractmethod
    def read_file(self, path: str) -> str:
        """
        Read a file from the sandbox filesystem.

        Args:
            path: Virtual path within the sandbox workdir.

        Returns:
            File contents as a string.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        ...

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """
        Write content to a file in the sandbox filesystem.

        Creates intermediate directories as needed.

        Args:
            path: Virtual path within the sandbox workdir.
            content: String content to write.
        """
        ...

    @abstractmethod
    def list_dir(self, path: str = ".") -> list[str]:
        """
        List entries in a sandbox directory.

        Args:
            path: Virtual directory path (default: workdir root).

        Returns:
            List of entry names.
        """
        ...

    @abstractmethod
    def get_workdir(self) -> str:
        """Return the absolute host path of the sandbox workdir."""
        ...
