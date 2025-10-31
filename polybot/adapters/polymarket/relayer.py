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
        raw = self._client.place_orders(payload)
        acks: List[OrderAck] = []
        for a in raw:
            acks.append(
                OrderAck(
                    order_id=str(a.get("order_id", "")),
                    accepted=bool(a.get("accepted", False)),
                    filled_size=float(a.get("filled_size", 0.0)),
                    remaining_size=float(a.get("remaining_size", 0.0)),
                    status=str(a.get("status", "accepted")),
                    client_order_id=a.get("client_order_id"),
                )
            )
        return acks

    def cancel_client_orders(self, client_order_ids: List[str]) -> List[CancelAck]:
        raw = self._client.cancel_orders(client_order_ids)
        return [CancelAck(client_order_id=str(a.get("client_order_id", "")), canceled=bool(a.get("canceled", False))) for a in raw]


def build_relayer(kind: str, **kwargs):
    kind = (kind or "fake").lower()
    if kind == "fake":
        fill_ratio = float(kwargs.get("fill_ratio", 0.0))
        return FakeRelayer(fill_ratio=fill_ratio)
    if kind == "real":
        client = kwargs.get("client")
        if client is None:
            raise NotImplementedError("Real relayer requires an injected client instance (py-clob-client)")
        return RelayerClient(client)
    raise ValueError(f"Unknown relayer kind: {kind}")
