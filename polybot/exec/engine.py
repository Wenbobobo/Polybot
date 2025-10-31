from __future__ import annotations

from dataclasses import dataclass
from typing import List

from polybot.exec.planning import ExecutionPlan
from polybot.adapters.polymarket.relayer import OrderRequest, FakeRelayer, OrderAck


@dataclass
class ExecutionResult:
    acks: List[OrderAck]
    fully_filled: bool


class ExecutionEngine:
    def __init__(self, relayer: FakeRelayer):
        self.relayer = relayer

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
        return ExecutionResult(acks=acks, fully_filled=fully)

