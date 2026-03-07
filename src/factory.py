"""
Reflection Factory — dynamically loads classes/instances from config strings.

Usage in config.yaml:
    use: "langchain_openai:ChatOpenAI"
    use: "src.models.patched_deepseek:PatchedChatDeepSeek"

The `resolve_class` function parses "package.module:ClassName" strings and
returns the class or callable. `build_from_config` additionally instantiates
the class using the remaining config dict keys.
"""
from __future__ import annotations

import importlib
import os
from typing import Any


def resolve_class(use_str: str) -> Any:
    """
    Dynamically load and return a class/variable from a dotted module path.

    Args:
        use_str: A string of the form "package.module:ClassName" or
                 "package.module:variable_name".

    Returns:
        The class or object referenced by the string.

    Raises:
        ValueError: If the string is malformed.
        ImportError: If the module cannot be imported.
        AttributeError: If the name does not exist in the module.
    """
    if ":" not in use_str:
        raise ValueError(
            f"Invalid 'use' string '{use_str}'. "
            "Expected format: 'package.module:ClassName'"
        )

    module_path, attr_name = use_str.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve $ENV_VAR references in config values."""
    if isinstance(value, str) and value.startswith("$"):
        env_key = value[1:]
        return os.environ.get(env_key, "")
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def build_from_config(config: dict[str, Any]) -> Any:
    """
    Instantiate a class from a config dict that contains a 'use' key.

    The 'use' key is extracted and resolved; remaining keys become kwargs
    passed to the class constructor. Environment variable substitution is
    applied to all values.

    Args:
        config: A dict with at least a 'use' key.

    Returns:
        An instance of the resolved class.

    Example::

        build_from_config({
            "use": "langchain_openai:ChatOpenAI",
            "model": "gpt-4o",
            "api_key": "$OPENAI_API_KEY",
        })
    """
    config = dict(config)  # shallow copy
    use_str = config.pop("use")
    klass = resolve_class(use_str)

    # Resolve env vars
    kwargs = {k: _resolve_env_vars(v) for k, v in config.items()}

    # Skip keys that are not standard init params
    _meta_keys = {"name", "display_name", "group", "supports_thinking", "supports_vision"}
    init_kwargs = {k: v for k, v in kwargs.items() if k not in _meta_keys}

    return klass(**init_kwargs)
