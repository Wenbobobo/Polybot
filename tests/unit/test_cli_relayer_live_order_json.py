import json
from polybot.cli.commands import cmd_relayer_live_order
from polybot.adapters.polymarket.relayer import OrderAck


class _StubRelayer:
    def __init__(self, fill_ratio: float = 1.0):
        self.fill_ratio = fill_ratio

    def place_orders(self, reqs, idempotency_prefix=None):
        # mimic deterministic full fills with OrderAck objects
        acks = []
        for i, r in enumerate(reqs, start=1):
            acks.append(
                OrderAck(
                    order_id=f"ord-{i}",
                    accepted=True,
                    filled_size=float(getattr(r, "size", 0.0)),
                    remaining_size=0.0,
                    status="filled",
                    client_order_id=getattr(r, "client_order_id", None),
                )
            )
        return acks


def test_cmd_relayer_live_order_as_json(monkeypatch):
    def _build_relayer(kind: str, **kwargs):
        return _StubRelayer()

    monkeypatch.setattr("polybot.cli.commands.build_relayer", _build_relayer)
    out = cmd_relayer_live_order(
        market_id="m1",
        outcome_id="yes",
        side="buy",
        price=0.5,
        size=1.0,
        base_url="https://clob.polymarket.com",
        private_key="0xabc",
        chain_id=137,
        timeout_s=1.0,
        confirm_live=True,
        as_json=True,
    )
    data = json.loads(out)
    assert data["placed"] == 1
    assert data["accepted"] == 1
    # status breakdown should include filled=1
    assert data["statuses"].get("filled", 0) == 1
