from __future__ import annotations

from typing import List, Optional, Dict, Any

from .relayer import OrderRequest, OrderAck


class PyClobRelayer:
    """Adapter for py-clob-client style relayer.

    Expects an injected `client` with:
      - place_orders(list[dict]) -> list[dict]
      - cancel_orders(list[str]) -> list[dict]

    Payload mapping tries multiple common key names to accommodate client variants:
      - client_order_id | clientOrderId
      - idempotency_key | idempotencyKey
      - time_in_force | timeInForce | tif
      - response fields: order_id | orderId, filled_size | filledSize, remaining_size | remainingSize, status
    """

    def __init__(self, client: object):
        self._client = client

    @staticmethod
    def _resp_get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in d:
                return d[k]
        return default

    def place_orders(self, reqs: List[OrderRequest], idempotency_prefix: Optional[str] = None) -> List[OrderAck]:
        payload: List[Dict[str, Any]] = []
        for r in reqs:
            o: Dict[str, Any] = {
                "market": r.market_id,
                "outcome": r.outcome_id,
                "side": r.side,
                "price": r.price,
                "size": r.size,
                "timeInForce": r.tif,
            }
            if r.client_order_id:
                o["clientOrderId"] = r.client_order_id
            if idempotency_prefix and r.client_order_id:
                o["idempotencyKey"] = f"{idempotency_prefix}:{r.client_order_id}"
            payload.append(o)
        raw = self._client.place_orders(payload)
        acks: List[OrderAck] = []
        for a in raw:
            acks.append(
                OrderAck(
                    order_id=str(self._resp_get(a, "order_id", "orderId", default="")),
                    accepted=bool(self._resp_get(a, "accepted", default=False) or (self._resp_get(a, "status") not in ("rejected", False, None))),
                    filled_size=float(self._resp_get(a, "filled_size", "filledSize", default=0.0) or 0.0),
                    remaining_size=float(self._resp_get(a, "remaining_size", "remainingSize", default=0.0) or 0.0),
                    status=str(self._resp_get(a, "status", default="accepted")),
                    client_order_id=self._resp_get(a, "client_order_id", "clientOrderId"),
                )
            )
        return acks

    def cancel_client_orders(self, client_order_ids: List[str]):
        raw = self._client.cancel_orders(client_order_ids)
        return [
            {
                "client_order_id": self._resp_get(a, "client_order_id", "clientOrderId", default=""),
                "canceled": bool(self._resp_get(a, "canceled", default=False)),
            }
            for a in raw
        ]

