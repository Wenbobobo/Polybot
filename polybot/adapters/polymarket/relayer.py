from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Dict


TimeInForce = Literal["IOC", "FOK", "GTC"]


@dataclass
class OrderRequest:
    market_id: str
    outcome_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    tif: TimeInForce = "IOC"
    client_order_id: Optional[str] = None


@dataclass
class OrderAck:
    order_id: str
    accepted: bool
    filled_size: float = 0.0
    remaining_size: float = 0.0
    status: Literal["accepted", "rejected", "filled", "partial"] = "accepted"
    client_order_id: Optional[str] = None


@dataclass
class CancelAck:
    client_order_id: str
    canceled: bool


class FakeRelayer:
    """A deterministic fake relayer for tests/integration without network.

    Rules:
    - Accepts all orders with price in [0,1] and size>0
    - Can be configured with a fill_ratio to simulate partial fills
    """

    def __init__(self, fill_ratio: float = 1.0):
        self.fill_ratio = max(0.0, min(1.0, fill_ratio))
        self._seq = 0
        self._open: Dict[str, str] = {}  # client_oid -> order_id

    def place_orders(self, reqs: List[OrderRequest]) -> List[OrderAck]:
        acks: List[OrderAck] = []
        for r in reqs:
            self._seq += 1
            if not (0.0 <= r.price <= 1.0) or r.size <= 0:
                acks.append(OrderAck(order_id=f"ord-{self._seq}", accepted=False, status="rejected", client_order_id=r.client_order_id))
                continue
            filled = round(r.size * self.fill_ratio, 10)
            remaining = max(0.0, r.size - filled)
            status = "filled" if remaining == 0.0 else ("partial" if filled > 0.0 else "accepted")
            oid = f"ord-{self._seq}"
            acks.append(OrderAck(order_id=oid, accepted=True, filled_size=filled, remaining_size=remaining, status=status, client_order_id=r.client_order_id))
            if r.tif == "GTC" and r.client_order_id:
                self._open[r.client_order_id] = oid
        return acks

    def cancel_client_orders(self, client_order_ids: List[str]) -> List[CancelAck]:
        acks: List[CancelAck] = []
        for cid in client_order_ids:
            canceled = cid in self._open
            if canceled:
                self._open.pop(cid, None)
            acks.append(CancelAck(client_order_id=cid, canceled=canceled))
        return acks


class RelayerClient:
    """Adapter for a real Polymarket CLOB client (e.g., py-clob-client-like).

    This class depends on an injected client with methods:
      - place_orders(list[dict]) -> list[dict]
      - cancel_orders(list[str]) -> list[dict]

    No network calls are made in tests; pass a stub client implementing these methods.
    """

    def __init__(self, client: object):
        self._client = client

    def place_orders(self, reqs: List[OrderRequest], idempotency_prefix: Optional[str] = None) -> List[OrderAck]:
        payload = []
        for r in reqs:
            p: Dict[str, object] = {
                "market_id": r.market_id,
                "outcome_id": r.outcome_id,
                "side": r.side,
                "price": r.price,
                "size": r.size,
                "tif": r.tif,
                "client_order_id": r.client_order_id,
            }
            if idempotency_prefix and r.client_order_id:
                p["idempotency_key"] = f"{idempotency_prefix}:{r.client_order_id}"
            payload.append(p)
        try:
            raw = self._client.place_orders(payload)
        except Exception:
            # increment relayer_place_errors per market and re-raise
            try:
                from polybot.observability.metrics import inc_labelled  # local import to avoid cycles

                for r in reqs:
                    inc_labelled("relayer_place_errors", {"market": r.market_id}, 1)
            except Exception:
                pass
            raise
        acks: List[OrderAck] = []
        for a in raw:
            # accept variant keys and infer acceptance from status if accepted missing
            status = str(a.get("status", "")).lower()
            accepted_flag = a.get("accepted")
            if accepted_flag is None:
                accepted_flag = status in ("accepted", "filled", "partial")
            client_oid = a.get("client_order_id") or a.get("clientOrderId")
            order_id = a.get("order_id") or a.get("orderId") or ""
            filled = a.get("filled_size") if a.get("filled_size") is not None else a.get("filledSize", 0.0)
            remaining = a.get("remaining_size") if a.get("remaining_size") is not None else a.get("remainingSize", 0.0)
            acks.append(
                OrderAck(
                    order_id=str(order_id),
                    accepted=bool(accepted_flag),
                    filled_size=float(filled or 0.0),
                    remaining_size=float(remaining or 0.0),
                    status=str(a.get("status", "accepted")),
                    client_order_id=client_oid,
                )
            )
        return acks

    def cancel_client_orders(self, client_order_ids: List[str]) -> List[CancelAck]:
        try:
            raw = self._client.cancel_orders(client_order_ids)
        except Exception:
            try:
                from polybot.observability.metrics import inc

                inc("relayer_cancel_errors_total", 1)
            except Exception:
                pass
            raise
        out: List[CancelAck] = []
        for a in raw:
            cid = a.get("client_order_id") or a.get("clientOrderId") or ""
            canceled = a.get("canceled")
            if canceled is None:
                # accept status variants
                status = str(a.get("status", "")).lower()
                canceled = status == "canceled"
            out.append(CancelAck(client_order_id=str(cid), canceled=bool(canceled)))
        return out

    # Optional allowance helpers — forwarded if underlying client exposes them (snake or camel).
    def approve_usdc(self, amount: float):  # pragma: no cover - exercised via dedicated tests
        inner = self._client
        if hasattr(inner, "approve_usdc"):
            return getattr(inner, "approve_usdc")(amount)
        if hasattr(inner, "approveUsdc"):
            return getattr(inner, "approveUsdc")(amount)
        raise NotImplementedError("approve_usdc not available on underlying client")

    def approve_outcome(self, token_address: str, amount: float):  # pragma: no cover
        inner = self._client
        if hasattr(inner, "approve_outcome"):
            return getattr(inner, "approve_outcome")(token_address, amount)
        if hasattr(inner, "approveOutcome"):
            return getattr(inner, "approveOutcome")(token_address, amount)
        raise NotImplementedError("approve_outcome not available on underlying client")


class RetryRelayer:
    """Wrapper that adds retry/backoff around place/cancel operations.

    Retries on exceptions up to max_retries with optional sleep between attempts.
    Increments relayer_retries_total on each retry attempt.
    """

    def __init__(self, inner, max_retries: int = 0, retry_sleep_ms: int = 0, sleeper=None):
        self._inner = inner
        self._max_retries = max(0, int(max_retries))
        self._retry_sleep_ms = max(0, int(retry_sleep_ms))
        self._sleeper = sleeper

    def place_orders(self, reqs: List[OrderRequest], idempotency_prefix: Optional[str] = None) -> List[OrderAck]:
        attempt = 0
        while True:
            try:
                return self._inner.place_orders(reqs, idempotency_prefix=idempotency_prefix)
            except Exception:
                attempt += 1
                try:
                    from polybot.observability.metrics import inc

                    inc("relayer_retries_total", 1)
                    # classify rate-limit style errors
                    try:
                        import sys
                        _etype, e, _tb = sys.exc_info()
                        code = getattr(e, "code", None)
                        msg = str(e) if e else ""
                        if code == 429 or (isinstance(msg, str) and "rate limit" in msg.lower()):
                            inc("relayer_rate_limited_total", 1)
                        if isinstance(e, TimeoutError) or (isinstance(msg, str) and "timeout" in msg.lower()):
                            inc("relayer_timeouts_total", 1)
                    except Exception:
                        pass
                except Exception:
                    pass
                if attempt > self._max_retries:
                    raise
                if self._sleeper:
                    try:
                        self._sleeper(self._retry_sleep_ms)
                    except Exception:
                        pass
                else:
                    import time as _t

                    _t.sleep(self._retry_sleep_ms / 1000.0)

    def cancel_client_orders(self, client_order_ids: List[str]) -> List[CancelAck]:
        attempt = 0
        while True:
            try:
                if hasattr(self._inner, "cancel_client_orders"):
                    return self._inner.cancel_client_orders(client_order_ids)
                return []
            except Exception:
                attempt += 1
                try:
                    from polybot.observability.metrics import inc

                    inc("relayer_retries_total", 1)
                    try:
                        import sys
                        _etype, e, _tb = sys.exc_info()
                        code = getattr(e, "code", None)
                        msg = str(e) if e else ""
                        if code == 429 or (isinstance(msg, str) and "rate limit" in msg.lower()):
                            inc("relayer_rate_limited_total", 1)
                        if isinstance(e, TimeoutError) or (isinstance(msg, str) and "timeout" in msg.lower()):
                            inc("relayer_timeouts_total", 1)
                    except Exception:
                        pass
                except Exception:
                    pass
                if attempt > self._max_retries:
                    raise
                if self._sleeper:
                    try:
                        self._sleeper(self._retry_sleep_ms)
                    except Exception:
                        pass
                else:
                    import time as _t

                    _t.sleep(self._retry_sleep_ms / 1000.0)

    def __getattr__(self, name):
        # Forward unknown attributes/methods (e.g., approve_usdc) to inner
        return getattr(self._inner, name)


def build_relayer(kind: str, **kwargs):
    kind = (kind or "fake").lower()
    if kind == "fake":
        fill_ratio = float(kwargs.get("fill_ratio", 0.0))
        rel = FakeRelayer(fill_ratio=fill_ratio)
        # optional wrapper
        mr = int(kwargs.get("max_retries", 0))
        rs = int(kwargs.get("retry_sleep_ms", 0))
        if mr > 0:
            return RetryRelayer(rel, max_retries=mr, retry_sleep_ms=rs)
        return rel
    if kind == "real":
        client = kwargs.get("client")
        if client is None:
            # attempt to build via py-clob helper if available
            try:
                from .real_client import make_pyclob_client  # type: ignore
                base_url = str(kwargs.get("base_url", "https://clob.polymarket.com"))
                private_key = str(kwargs.get("private_key", ""))
                dry_run = bool(kwargs.get("dry_run", True))
                # forward extra kwargs (e.g., chain_id, timeout_s)
                extras = {k: v for k, v in kwargs.items() if k not in {"client", "base_url", "private_key", "dry_run"}}
                client = make_pyclob_client(base_url=base_url, private_key=private_key, dry_run=dry_run, **extras)
            except Exception as e:  # noqa: BLE001
                raise NotImplementedError(
                    "Real relayer requires an injected client instance or install py-clob-client"
                ) from e
        # Prefer the py-clob adapter for real clients so that request/response
        # mapping and idempotency keys match the official client.
        try:
            from .pyclob_adapter import PyClobRelayer  # type: ignore

            rel = PyClobRelayer(client)
        except Exception:
            # Fallback to generic mapping if adapter import fails
            rel = RelayerClient(client)
        # Optional retry wrapper
        mr = int(kwargs.get("max_retries", 0))
        rs = int(kwargs.get("retry_sleep_ms", 0))
        if mr > 0:
            return RetryRelayer(rel, max_retries=mr, retry_sleep_ms=rs)
        return rel
    raise ValueError(f"Unknown relayer kind: {kind}")
