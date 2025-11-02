from __future__ import annotations

from typing import Any


def make_pyclob_client(base_url: str, private_key: str, dry_run: bool = True, **kwargs: Any) -> Any:
    """Construct a py-clob-client instance from settings.

    This function defers the import and raises NotImplementedError with a friendly message
    when the dependency is not available. It intentionally avoids reading env vars; callers
    must pass settings explicitly (config files elsewhere).
    """
    try:
        # Example import path; adjust when integrating the actual client.
        from py_clob_client import ClobClient  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise NotImplementedError(
            "py-clob-client is not installed. Install and provide signer to enable real relayer."
        ) from e

    # Normalize a few well-known aliases before forwarding, to improve
    # compatibility with differing client ctor signatures.
    # Map timeout_s -> timeout if present.
    if "timeout_s" in kwargs and "timeout" not in kwargs:
        kwargs["timeout"] = kwargs.pop("timeout_s")

    # Placeholder construction; actual constructor may differ.
    # Forward any extra kwargs (e.g., network/chain/timeouts) to the client ctor
    client = ClobClient(base_url=base_url, private_key=private_key, dry_run=dry_run, **kwargs)
    return client
