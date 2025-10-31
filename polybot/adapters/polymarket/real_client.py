from __future__ import annotations

from typing import Any


def make_pyclob_client(base_url: str, private_key: str, dry_run: bool = True) -> Any:
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

    # Placeholder construction; actual constructor may differ.
    client = ClobClient(base_url=base_url, private_key=private_key, dry_run=dry_run)
    return client

