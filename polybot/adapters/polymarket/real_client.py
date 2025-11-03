from __future__ import annotations

from typing import Any
import inspect


def make_pyclob_client(base_url: str, private_key: str, dry_run: bool = True, **kwargs: Any) -> Any:
    """Construct a py-clob-client instance from settings.

    This function defers the import and raises NotImplementedError with a friendly message
    when the dependency is not available. It intentionally avoids reading env vars; callers
    must pass settings explicitly (config files elsewhere).
    """
    try:
        # Prefer top-level import to play nicely with test stubs; fallback to submodule path.
        try:
            from py_clob_client import ClobClient  # type: ignore
        except Exception:
            from py_clob_client.client import ClobClient  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise NotImplementedError(
            "py-clob-client is not installed. Install and provide signer to enable real relayer."
        ) from e

    # Normalize a few well-known aliases before forwarding, to improve
    # compatibility with differing client ctor signatures.
    # Map timeout_s -> timeout if present.
    if "timeout_s" in kwargs and "timeout" not in kwargs:
        kwargs["timeout"] = kwargs.pop("timeout_s")

    # If no private_key provided, construct a read-only client for market discovery.
    if not private_key:
        # Filter kwargs to only what ClobClient supports (e.g., timeout, chain_id)
        ro_kwargs: dict[str, Any] = {}
        try:
            sig_ro = inspect.signature(ClobClient)
            params_ro = set(sig_ro.parameters.keys())
        except Exception:
            params_ro = set()
        # normalize timeout_s -> timeout already handled above
        for k in ("timeout", "chain_id", "creds", "signature_type", "funder"):
            if k in kwargs and (not params_ro or k in params_ro):
                ro_kwargs[k] = kwargs[k]
        # Try positional host with filtered kwargs; then keyword host; then base_url kw
        try:
            return ClobClient(base_url, **ro_kwargs)
        except TypeError:
            pass
        try:
            if not params_ro or "host" in params_ro:
                return ClobClient(host=base_url, **ro_kwargs)
        except TypeError:
            pass
        # Last resort: keep backward compatibility for tests expecting base_url kw
        return ClobClient(base_url=base_url, **ro_kwargs)

    # Private key provided: attempt to map to expected parameter names.
    sig = None
    try:
        sig = inspect.signature(ClobClient)
    except Exception:
        sig = None
    ctor_kwargs: dict[str, Any] = {}
    # Host/base param: pass as positional to avoid kw mismatches.
    # Key parameter name may be 'key' or 'private_key'.
    params = set(sig.parameters.keys()) if sig else set()
    if "key" in params:
        ctor_kwargs["key"] = private_key
    else:
        ctor_kwargs["private_key"] = private_key
    # Forward common extras
    if "chain_id" in kwargs and (not sig or "chain_id" in params):
        ctor_kwargs["chain_id"] = kwargs["chain_id"]
    if "dry_run" in params:
        ctor_kwargs["dry_run"] = dry_run
    if "timeout" in kwargs and (sig and "timeout" in params):
        ctor_kwargs["timeout"] = kwargs["timeout"]
    # Include remaining extras verbatim (do not overwrite already set keys)
    for k, v in kwargs.items():
        if k not in ctor_kwargs and k not in ("timeout_s",):
            ctor_kwargs[k] = v
    try:
        return ClobClient(base_url, **ctor_kwargs)
    except TypeError:
        # Fallback to keyword host if positional fails for this client
        try:
            return ClobClient(host=base_url, **ctor_kwargs)
        except Exception:
            # Final fallback: base_url kw for test stubs
            return ClobClient(base_url=base_url, **ctor_kwargs)
    except Exception as e:  # pragma: no cover - environment-dependent
        # If real client exists but cannot be constructed (e.g., missing chain_id),
        # surface a consistent NotImplementedError to match tests' expectations.
        raise NotImplementedError("py-clob-client unavailable or invalid constructor") from e
