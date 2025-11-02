from pathlib import Path
from polybot.cli.commands import cmd_orders_cancel_client_oids
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


class StubRelayer:
    def __init__(self):
        self.canceled = []

    def cancel_client_orders(self, oids):  # type: ignore[no-untyped-def]
        self.canceled.append(list(oids))
        return [{"client_order_id": o, "canceled": True} for o in oids]


def test_cli_orders_cancel_updates_db_and_calls_relayer(monkeypatch, tmp_path: Path):
    db_url = f"sqlite:///{(tmp_path/'test.db').as_posix()}"
    con = connect_sqlite(db_url)
    schema.create_all(con)
    con.execute(
        "INSERT INTO orders (order_id, client_oid, market_id, outcome_id, side, price, size, tif, status, created_ts_ms) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("o1", "c1", "m1", "o", "buy", 0.4, 1.0, "GTC", "accepted", 1),
    )
    con.commit()
    stub = StubRelayer()
    # Patch engine builder path by injecting a fake build_relayer usage via monkeypatch
    from polybot.cli import commands as cmds

    monkeypatch.setattr(cmds, "build_relayer", lambda *a, **k: stub)
    out = cmd_orders_cancel_client_oids("c1", db_url=db_url, relayer_type="real", private_key="0x" + "1" * 64)
    assert out.startswith("canceled=1")
    row = con.execute("SELECT status FROM orders WHERE client_oid='c1'").fetchone()[0]
    assert row == "canceled"
    assert stub.canceled and stub.canceled[0] == ["c1"]
