from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.observability.metrics import get_counter_labelled
from .commands import parse_command


@dataclass
class BotContext:
    market_id: str
    outcome_yes_id: str


class BotAgent:
    def __init__(self, engine: ExecutionEngine, ctx: BotContext):
        self.engine = engine
        self.ctx = ctx

    def handle_text(self, text: str) -> str:
        pc = parse_command(text)
        if pc.cmd in ("help", "h"):
            return "commands: /status, /buy <price> <size>, /sell <price> <size>"
        if pc.cmd == "status":
            mkt = self.ctx.market_id
            placed = get_counter_labelled("orders_placed", {"market": mkt})
            filled = get_counter_labelled("orders_filled", {"market": mkt})
            return f"status: market={mkt} orders placed={placed} filled={filled}"
        if pc.cmd in ("buy", "sell"):
            try:
                price = float(pc.args[0])
                size = float(pc.args[1])
            except Exception:
                return "usage: /buy <price> <size>"
            side = pc.cmd
            it = OrderIntent(market_id=self.ctx.market_id, outcome_id=self.ctx.outcome_yes_id, side=side, price=price, size=size, tif="IOC")
            plan = ExecutionPlan(intents=[it], expected_profit=0.0, rationale=f"tg_{side}")
            res = self.engine.execute_plan(plan)
            return f"ok: placed {len(res.acks)}"
        return "unknown command"

