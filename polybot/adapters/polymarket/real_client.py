from __future__ import annotations

from typing import Any, List, Dict
import inspect
import math


def _pop_known(options: Dict[str, Any], key: str, default: Any = None) -> Any:
    if key in options:
        return options.pop(key)
    return default


def _map_time_in_force(value: str):
    try:
        from py_clob_client.clob_types import OrderType  # type: ignore
    except Exception:  # pragma: no cover - handled earlier during import gating
        return "FAK" if str(value).upper() == "IOC" else str(value).upper()
    upper = (value or "").upper()
    if upper in ("IOC", "FAK"):
        return OrderType.FAK
    if upper == "FOK":
        return OrderType.FOK
    if upper == "GTD":
        return OrderType.GTD
    return OrderType.GTC


class _ClobClientOrderBridge:
    """Adapter that gives py-clob-client's ClobClient a place_orders/cancel_orders surface."""

    def __init__(self, client: Any, *, dry_run: bool):
        self._client = client
        self._dry_run = dry_run
        self._ensure_creds()

    def _ensure_creds(self, force: bool = False) -> None:
        try:
            creds = getattr(self._client, "creds", None)
            if not force and creds and getattr(creds, "api_key", None):
                return
            if hasattr(self._client, "create_or_derive_api_creds") and hasattr(self._client, "set_api_creds"):
                derived = self._client.create_or_derive_api_creds()
                self._client.set_api_creds(derived)
        except Exception:  # pragma: no cover - best-effort only
            pass

    def place_orders(self, orders: List[Dict[str, Any]], idempotency_prefix: str | None = None) -> List[Dict[str, Any]]:
        if self._dry_run:
            out: List[Dict[str, Any]] = []
            for order in orders:
                out.append(
                    {
                        "orderId": "",
                        "status": "dry_run",
                        "accepted": False,
                        "clientOrderId": order.get("clientOrderId") or order.get("client_order_id") or "",
                    }
                )
            return out
        try:
            from py_clob_client.clob_types import OrderArgs, PostOrdersArgs  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise NotImplementedError("py-clob-client types unavailable for order placement") from exc

        payload: List[Any] = []
        client_order_ids: List[str] = []
        for order in orders:
            side = str(order.get("side", "")).upper()
            args = OrderArgs(
                token_id=str(order.get("outcome") or order.get("token_id") or ""),
                price=float(order.get("price", 0.0)),
                size=float(order.get("size", 0.0)),
                side=side,
            )
            signed = self._client.create_order(args)
            tif = _map_time_in_force(str(order.get("timeInForce") or order.get("tif") or "GTC"))
            payload.append(PostOrdersArgs(order=signed, orderType=tif))
            client_order_ids.append(str(order.get("clientOrderId") or order.get("client_order_id") or ""))
        self._ensure_creds()
        try:
            raw = self._client.post_orders(payload)
        except Exception as exc:
            msg = str(exc)
            if "API Credentials" in msg or "L2_AUTH_UNAVAILABLE" in msg:
                self._ensure_creds(force=True)
                raw = self._client.post_orders(payload)
            else:
                raise
        acks: List[Dict[str, Any]] = []
        for idx, client_resp in enumerate(raw or []):
            client_oid = client_order_ids[idx] if idx < len(client_order_ids) else ""
            error_msg = client_resp.get("errorMsg") or client_resp.get("error")
            success_flag = bool(client_resp.get("success"))
            status_raw = str(client_resp.get("status") or "").lower()

            accepted = success_flag and not error_msg and status_raw not in ("rejected", "failed", "error")
            if accepted and status_raw and status_raw not in ("accepted", "filled", "partial"):
                accepted = False

            if accepted:
                status_value = status_raw or "accepted"
            else:
                if status_raw in ("partial", "filled"):
                    status_value = status_raw
                    accepted = True
                else:
                    status_value = status_raw or "rejected"

            filled = float(client_resp.get("filledSize") or client_resp.get("filled_size") or 0.0)
            remaining = float(client_resp.get("remainingSize") or client_resp.get("remaining_size") or 0.0)
            # sanitize NaNs from unlucky client responses
            if math.isnan(filled):
                filled = 0.0
            if math.isnan(remaining):
                remaining = 0.0
            acks.append(
                {
                    "orderId": client_resp.get("orderID") or client_resp.get("orderId") or "",
                    "status": status_value,
                    "accepted": accepted,
                    "filledSize": filled,
                    "remainingSize": remaining,
                    "clientOrderId": client_oid,
                    "error": error_msg,
                }
            )
        # If the response length mismatches requests, pad remaining entries with synthetic rejects
        while len(acks) < len(client_order_ids):
            coid = client_order_ids[len(acks)]
            acks.append(
                {
                    "orderId": "",
                    "status": "rejected",
                    "accepted": False,
                    "filledSize": 0.0,
                    "remainingSize": 0.0,
                    "clientOrderId": coid,
                    "error": "post_orders returned fewer results than requested",
                }
            )
        return acks

    def cancel_orders(self, client_order_ids: List[str]) -> List[Dict[str, Any]]:
        if not hasattr(self._client, "cancel_orders"):
            return []
        raw = self._client.cancel_orders(client_order_ids)
        out: List[Dict[str, Any]] = []
        for idx, cid in enumerate(client_order_ids):
            resp = raw[idx] if isinstance(raw, list) and idx < len(raw) else {}
            resolved = resp.get("clientOrderId") or resp.get("client_order_id") or cid
            canceled = bool(resp.get("success") or resp.get("canceled") or (resp.get("status") == "canceled"))
            out.append({"client_order_id": resolved, "canceled": canceled})
        return out

    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)


def make_pyclob_client(base_url: str, private_key: str, dry_run: bool = True, **kwargs: Any) -> Any:
    """Construct a py-clob-client instance from settings.

    This function defers the import and raises NotImplementedError with a friendly message
    when the dependency is not available. It intentionally avoids reading env vars; callers
    must pass settings explicitly (config files elsewhere).
    """
    try:
        try:
            from py_clob_client import ClobClient  # type: ignore
        except Exception:
            from py_clob_client.client import ClobClient  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise NotImplementedError(
            "py-clob-client is not installed. Install and provide signer to enable real relayer."
        ) from e

    extras = dict(kwargs)  # copy to avoid mutating caller state
    timeout = _pop_known(extras, "timeout_s")
    if timeout is None:
        timeout = _pop_known(extras, "timeout")
    chain_id = _pop_known(extras, "chain_id", None)
    creds = _pop_known(extras, "creds", None)
    signature_type = _pop_known(extras, "signature_type", None)
    funder = _pop_known(extras, "funder", None)
    builder_config = _pop_known(extras, "builder_config", None)

    params = {}
    has_var_kw = False
    try:
        sig = inspect.signature(ClobClient)
        params = sig.parameters
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    except (TypeError, ValueError):
        params = {}
        has_var_kw = True

    if not private_key:
        # Read-only client for catalog usage: prefer positional host path, avoid kwargs.
        for call in (
            lambda: ClobClient(base_url),
            lambda: ClobClient(host=base_url),
            lambda: ClobClient(base_url=base_url),
        ):
            try:
                return call()
            except TypeError:
                continue
        return ClobClient(base_url)

    ctor_kwargs: Dict[str, Any] = {}
    if "private_key" in params:
        ctor_kwargs["private_key"] = private_key
    elif "key" in params:
        ctor_kwargs["key"] = private_key
    else:
        ctor_kwargs["private_key"] = private_key

    if "dry_run" in params or has_var_kw:
        ctor_kwargs["dry_run"] = dry_run
    if (chain_id is not None) and ("chain_id" in params or has_var_kw):
        ctor_kwargs["chain_id"] = chain_id
    if (timeout is not None) and ("timeout" in params or has_var_kw):
        ctor_kwargs["timeout"] = timeout
    if creds is not None and ("creds" in params or has_var_kw):
        ctor_kwargs["creds"] = creds
    if signature_type is not None and ("signature_type" in params or has_var_kw):
        ctor_kwargs["signature_type"] = signature_type
    if funder is not None and ("funder" in params or has_var_kw):
        ctor_kwargs["funder"] = funder
    if builder_config is not None and ("builder_config" in params or has_var_kw):
        ctor_kwargs["builder_config"] = builder_config
    # Ignore remaining extras silently (e.g., retry configs).

    if private_key and chain_id is None and ("chain_id" in params):
        raise NotImplementedError("py-clob-client requires chain_id when using a private key")

    # Try positional host first, then keyword fallbacks.
    client: Any | None = None
    for call in (
        lambda: ClobClient(base_url, **ctor_kwargs),
        lambda: ClobClient(host=base_url, **ctor_kwargs),
        lambda: ClobClient(base_url=base_url, **ctor_kwargs),
    ):
        try:
            client = call()
            break
        except TypeError:
            client = None
            continue
    if client is None:
        client = ClobClient(base_url, **ctor_kwargs)

    if timeout and not hasattr(client, "timeout"):
        try:
            setattr(client, "_timeout", timeout)
        except Exception:
            pass
    return client


def wrap_clob_client(client: Any, *, dry_run: bool) -> Any:
    """Ensure the given client exposes place_orders/cancel_orders."""
    if client is None:
        return None
    if hasattr(client, "place_orders") and callable(getattr(client, "place_orders")):
        return client
    if hasattr(client, "create_order") and hasattr(client, "post_orders"):
        return _ClobClientOrderBridge(client, dry_run=dry_run)
    return client
