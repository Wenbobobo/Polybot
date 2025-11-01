from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import List, Optional, Callable
import uuid
import inspect

from polybot.exec.planning import ExecutionPlan
from polybot.adapters.polymarket.relayer import OrderRequest, FakeRelayer, OrderAck
from polybot.storage.orders import persist_orders_and_fills, mark_canceled_by_client_oids
from polybot.observability.metrics import inc, inc_labelled, Timer


@dataclass
class ExecutionResult:
    acks: List[OrderAck]
    fully_filled: bool


class ExecutionEngine:
    def __init__(self, relayer: FakeRelayer, audit_db=None, max_retries: int = 0, retry_sleep_ms: int = 0, sleeper: Optional[Callable[[int], None]] = None):
        self.relayer = relayer
        self.audit_db = audit_db
        self.max_retries = max(0, int(max_retries))
        self.retry_sleep_ms = max(0, int(retry_sleep_ms))
        self._sleeper = sleeper

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        # Ensure plan_id for idempotency/audit
        plan_id = plan.plan_id or uuid.uuid4().hex
        # Populate client_order_id if missing
        for idx, it in enumerate(plan.intents):
            if not it.client_order_id:
                it.client_order_id = f"p-{plan_id[:8]}-{idx}-{it.side[0]}-{it.outcome_id}"
        reqs = [
            OrderRequest(
                market_id=i.market_id,
                outcome_id=i.outcome_id,
                side=i.side,  # type: ignore[arg-type]
                price=i.price,
                size=i.size,
                tif=i.tif,  # type: ignore[arg-type]
                client_order_id=i.client_order_id,
            )
            for i in plan.intents
        ]
        start_perf = time.perf_counter()
        with Timer("engine_execute_plan"):
            # Pass idempotency_prefix if relayer supports it
            acks: List[OrderAck]
            attempt = 0
            while True:
                try:
                    call_start = time.perf_counter()
                    sig = inspect.signature(self.relayer.place_orders)  # type: ignore[attr-defined]
                    if "idempotency_prefix" in sig.parameters:
                        acks = self.relayer.place_orders(reqs, idempotency_prefix=plan_id)  # type: ignore[arg-type]
                    else:
                        acks = self.relayer.place_orders(reqs)  # type: ignore[call-arg]
                    call_dur_ms = int((time.perf_counter() - call_start) * 1000)
                    # labelled duration per market for the relayer call itself
                    for mid in set(i.market_id for i in plan.intents):
                        inc_labelled("engine_place_call_ms_sum", {"market": mid}, call_dur_ms)
                        inc_labelled("engine_place_call_count", {"market": mid}, 1)
                    break
                except (TypeError, ValueError, AttributeError):
                    call_start = time.perf_counter()
                    acks = self.relayer.place_orders(reqs)  # type: ignore[call-arg]
                    call_dur_ms = int((time.perf_counter() - call_start) * 1000)
                    for mid in set(i.market_id for i in plan.intents):
                        inc_labelled("engine_place_call_ms_sum", {"market": mid}, call_dur_ms)
                        inc_labelled("engine_place_call_count", {"market": mid}, 1)
                    break
                except Exception:
                    attempt += 1
                    for mid in set(i.market_id for i in plan.intents):
                        inc_labelled("engine_retries", {"market": mid}, 1)
                    if attempt > self.max_retries:
                        # count error per market(s)
                        for mid in set(i.market_id for i in plan.intents):
                            inc_labelled("engine_errors", {"market": mid}, 1)
                        raise
                    if self._sleeper:
                        try:
                            self._sleeper(self.retry_sleep_ms)
                        except Exception:
                            pass
                    else:
                        import time as _t

                        _t.sleep(self.retry_sleep_ms / 1000.0)
        fully = all(a.remaining_size == 0.0 and a.accepted for a in acks)
        inc("orders_placed", len(reqs))
        inc("orders_filled", sum(1 for a in acks if a.remaining_size == 0.0 and a.accepted))
        # labelled per-market counters
        for it, ack in zip(plan.intents, acks):
            inc_labelled("orders_placed", {"market": it.market_id}, 1)
            if ack.remaining_size == 0.0 and ack.accepted:
                inc_labelled("orders_filled", {"market": it.market_id}, 1)
            # Relayer ack metrics by status and acceptance
            try:
                inc_labelled("relayer_acks", {"market": it.market_id, "status": str(ack.status)}, 1)
                if ack.accepted:
                    inc_labelled("relayer_acks_accepted", {"market": it.market_id}, 1)
                else:
                    inc_labelled("relayer_acks_rejected", {"market": it.market_id}, 1)
            except Exception:
                pass
        # labelled duration per market (same duration applied to all intents' markets in this simple model)
        dur_ms = int((time.perf_counter() - start_perf) * 1000)
        seen_markets = set(i.market_id for i in plan.intents)
        for mid in seen_markets:
            inc_labelled("engine_execute_plan_ms_sum", {"market": mid}, dur_ms)
            inc_labelled("engine_execute_plan_count", {"market": mid}, 1)
            inc_labelled("engine_place_ms_sum", {"market": mid}, dur_ms)
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
                duration_ms = int((time.perf_counter() - start_perf) * 1000)
                intents_json = json.dumps([i.__dict__ for i in plan.intents])
                acks_json = json.dumps([a.__dict__ for a in acks])
                self.audit_db.execute(
                    "INSERT INTO exec_audit (ts_ms, plan_id, duration_ms, plan_rationale, expected_profit, intents_json, acks_json) VALUES (?,?,?,?,?,?,?)",
                    (ts_ms, plan_id, duration_ms, plan.rationale, plan.expected_profit, intents_json, acks_json),
                )
                self.audit_db.commit()
            except Exception:
                pass
        return result

    def cancel_client_orders(self, client_order_ids: List[str]) -> None:
        # call relayer cancel if available
        if hasattr(self.relayer, "cancel_client_orders"):
            try:
                import time as _t
                from polybot.observability.metrics import inc

                _start = _t.perf_counter()
                self.relayer.cancel_client_orders(client_order_ids)
                dur_ms = int((_t.perf_counter() - _start) * 1000)
                inc("relayer_cancel_count", len(client_order_ids))
                inc("relayer_cancel_ms_sum", dur_ms)
            except Exception:
                pass
        # update DB statuses
        if self.audit_db is not None:
            try:
                mark_canceled_by_client_oids(self.audit_db, client_order_ids)
            except Exception:
                pass
