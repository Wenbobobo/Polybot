from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import List, Optional

from polybot.exec.planning import ExecutionPlan
from polybot.adapters.polymarket.relayer import OrderRequest, FakeRelayer, OrderAck
from polybot.storage.orders import persist_orders_and_fills, mark_canceled_by_client_oids


@dataclass
class ExecutionResult:
    acks: List[OrderAck]
    fully_filled: bool


class ExecutionEngine:
    def __init__(self, relayer: FakeRelayer, audit_db=None):
        self.relayer = relayer
        self.audit_db = audit_db

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        reqs = [
            OrderRequest(
                market_id=i.market_id,
                outcome_id=i.outcome_id,
                side=i.side,  # type: ignore[arg-type]
                price=i.price,
                size=i.size,
                tif=i.tif,  # type: ignore[arg-type]
            )
            for i in plan.intents
        ]
        acks = self.relayer.place_orders(reqs)
        fully = all(a.remaining_size == 0.0 and a.accepted for a in acks)
        result = ExecutionResult(acks=acks, fully_filled=fully)
        # persist orders/fills if DB configured
        if self.audit_db is not None:
            try:
                persist_orders_and_fills(self.audit_db, plan.intents, acks)
            except Exception:
                pass
        # optional audit persistence
        if self.audit_db is not None:
            try:
                ts_ms = int(time.time() * 1000)
                intents_json = json.dumps([i.__dict__ for i in plan.intents])
                acks_json = json.dumps([a.__dict__ for a in acks])
                self.audit_db.execute(
                    "INSERT INTO exec_audit (ts_ms, plan_rationale, expected_profit, intents_json, acks_json) VALUES (?,?,?,?,?)",
                    (ts_ms, plan.rationale, plan.expected_profit, intents_json, acks_json),
                )
                self.audit_db.commit()
            except Exception:
                pass
        return result

    def cancel_client_orders(self, client_order_ids: List[str]) -> None:
        # call relayer cancel if available
        if hasattr(self.relayer, "cancel_client_orders"):
            try:
                self.relayer.cancel_client_orders(client_order_ids)
            except Exception:
                pass
        # update DB statuses
        if self.audit_db is not None:
            try:
                mark_canceled_by_client_oids(self.audit_db, client_order_ids)
            except Exception:
                pass
