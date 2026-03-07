"""
Sandbox LangChain Tools — exposes sandbox operations as agent tools.

Each tool uses LocalSandboxProvider.get_current() to operate within the
current thread's isolated sandbox directory.
"""
from __future__ import annotations

from langchain_core.tools import tool

from src.sandbox.local import LocalSandboxProvider


@tool
def ls_tool(path: str = ".") -> str:
    """
    List files and directories in the sandbox working directory.

    Args:
        path: Relative path within the sandbox to list (default: root).

    Returns:
        Newline-separated list of entries.
    """
    sandbox = LocalSandboxProvider.get_current()
    try:
        entries = sandbox.list_dir(path)
        return "\n".join(entries) if entries else "(empty directory)"
    except NotADirectoryError as e:
        return f"[error] {e}"
    except Exception as e:
        return f"[error] {e}"


@tool
def read_file_tool(path: str) -> str:
    """
    Read the contents of a file in the sandbox.

    Args:
        path: Relative path to the file within the sandbox.

    Returns:
        File contents as a string, or an error message.
    """
    sandbox = LocalSandboxProvider.get_current()
    try:
        return sandbox.read_file(path)
    except FileNotFoundError:
        return f"[error] File not found: {path}"
    except PermissionError as e:
        return f"[error] {e}"
    except Exception as e:
        return f"[error] {e}"


@tool
def write_file_tool(path: str, content: str) -> str:
    """
    Write content to a file in the sandbox, creating directories as needed.

    Args:
        path: Relative path to the file within the sandbox.
        content: String content to write.

    Returns:
        Confirmation message or error.
    """
    sandbox = LocalSandboxProvider.get_current()
    try:
        sandbox.write_file(path, content)
        return f"File written: {path}"
    except PermissionError as e:
        return f"[error] {e}"
    except Exception as e:
        return f"[error] {e}"


@tool
def str_replace_tool(path: str, old_str: str, new_str: str) -> str:
    """
    Replace an exact string occurrence in a sandbox file.

    This is a surgical replacement — it replaces the first occurrence of
    old_str with new_str. Fails if old_str is not found.

    Args:
        path: Relative path to the file.
        old_str: Exact substring to find.
        new_str: Replacement string.

    Returns:
        Confirmation message or error.
    """
    sandbox = LocalSandboxProvider.get_current()
    try:
        content = sandbox.read_file(path)
        if old_str not in content:
            return f"[error] String not found in {path}: {repr(old_str[:80])}"
        new_content = content.replace(old_str, new_str, 1)
        sandbox.write_file(path, new_content)
        return f"String replaced in {path}"
    except FileNotFoundError:
        return f"[error] File not found: {path}"
    except Exception as e:
        return f"[error] {e}"


@tool
def bash_tool(command: str, timeout: int = 30) -> str:
    """
    Execute a bash command inside the isolated sandbox working directory.

    The command runs in the sandbox's dedicated workdir. stdout and stderr
    are combined and returned.

    Args:
        command: Shell command to execute.
        timeout: Maximum seconds to wait (default: 30).

    Returns:
        Combined stdout + stderr output.
    """
    sandbox = LocalSandboxProvider.get_current()
    return sandbox.execute_command(command, timeout=timeout)


# Convenience registry for config-driven tool loading
SANDBOX_TOOLS = {
    "ls": ls_tool,
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "str_replace": str_replace_tool,
    "bash": bash_tool,
}
