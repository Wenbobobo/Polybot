from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.storage.orders import persist_orders_and_fills_bulk
from polybot.exec.planning import OrderIntent
from polybot.adapters.polymarket.relayer import OrderAck


def test_orders_bulk_upsert_inserts_and_updates():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    intents = [
        OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0, tif="IOC", client_order_id="c1"),
        OrderIntent(market_id="m1", outcome_id="o2", side="sell", price=0.6, size=1.5, tif="IOC", client_order_id="c2"),
    ]
    acks = [
        OrderAck(order_id="ord-1", accepted=True, filled_size=0.5, remaining_size=0.5, status="partial", client_order_id="c1"),
        OrderAck(order_id="ord-2", accepted=True, filled_size=0.0, remaining_size=1.5, status="accepted", client_order_id="c2"),
    ]
    persist_orders_and_fills_bulk(con, intents, acks)
    cnt_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    cnt_fills = con.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    assert cnt_orders == 2 and cnt_fills == 1
    # Update status for ord-1 to filled
    acks2 = [
        OrderAck(order_id="ord-1", accepted=True, filled_size=0.5, remaining_size=0.0, status="filled", client_order_id="c1"),
        OrderAck(order_id="ord-2", accepted=True, filled_size=0.0, remaining_size=1.5, status="accepted", client_order_id="c2"),
    ]
    persist_orders_and_fills_bulk(con, intents, acks2)
    row = con.execute("SELECT status FROM orders WHERE order_id='ord-1'").fetchone()[0]
    assert row == "filled"

