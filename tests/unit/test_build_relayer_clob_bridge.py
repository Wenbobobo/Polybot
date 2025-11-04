import dataclasses

import pytest

from polybot.adapters.polymarket.relayer import build_relayer, OrderRequest


class _StubSignedOrder:
    def __init__(self, payload):
        self.payload = payload

    def dict(self):
        return self.payload


class _StubClobRaw:
    def __init__(self, *args, **kwargs):
        self.created = []
        self.posted = []
        self.cancelled = []
        self.creds = None

    def create_or_derive_api_creds(self):
        Creds = dataclasses.make_dataclass("Creds", [("api_key", str), ("api_secret", str), ("api_passphrase", str)])
        return Creds(api_key="k", api_secret="s", api_passphrase="p")

    def set_api_creds(self, creds):
        self.creds = creds

    def create_order(self, order_args, options=None):
        self.created.append((order_args, options))
        return _StubSignedOrder({"tokenId": order_args.token_id, "side": order_args.side})

    def post_orders(self, orders):
        self.posted.append(orders)
        return [
            {
                "orderID": "oid-1",
                "status": "accepted",
                "success": True,
            }
        ]

    def cancel_orders(self, ids):
        self.cancelled.append(ids)
        return [{"orderID": oid, "status": "canceled"} for oid in ids]


def _order_request(tif: str = "IOC") -> OrderRequest:
    return OrderRequest(
        market_id="market-1",
        outcome_id="token-yes",
        side="buy",
        price=0.42,
        size=2.0,
        tif=tif,
        client_order_id="cid-1",
    )


def test_build_relayer_wraps_clob_client(monkeypatch):
    raw = _StubClobRaw()

    class _Factory:
        def __call__(self, *args, **kwargs):
            return raw

    monkeypatch.setattr("py_clob_client.client.ClobClient", _Factory(), raising=True)

    rel = build_relayer(
        "real",
        base_url="https://clob.polymarket.com",
        private_key="0xabc",
        dry_run=False,
        chain_id=137,
    )

    acks = rel.place_orders([_order_request()], idempotency_prefix="plan-1")
    assert raw.created, "create_order should be invoked"
    created_args, _ = raw.created[0]
    assert created_args.token_id == "token-yes"
    assert created_args.side.upper() == "BUY"
    assert raw.posted, "post_orders should receive signed orders"
    assert acks and acks[0].order_id == "oid-1"
    assert acks[0].client_order_id == "cid-1"

    rel.cancel_client_orders(["cid-1"])
    assert raw.cancelled == [["cid-1"]]


@pytest.mark.parametrize(
    "tif,expected",
    [
        ("IOC", "FAK"),
        ("FOK", "FOK"),
        ("GTC", "GTC"),
    ],
)
def test_time_in_force_mapping(monkeypatch, tif, expected):
    raw = _StubClobRaw()

    class _Factory:
        def __call__(self, *args, **kwargs):
            return raw

    monkeypatch.setattr("py_clob_client.client.ClobClient", _Factory(), raising=True)

    rel = build_relayer(
        "real",
        base_url="https://clob.polymarket.com",
        private_key="0xabc",
        dry_run=False,
        chain_id=137,
    )
    rel.place_orders([_order_request(tif=tif)])
    assert raw.posted, "post_orders should be invoked"
    posted_arg = raw.posted[0][0]
    order_type = getattr(posted_arg, "orderType", None)
    assert order_type is not None
    value = getattr(order_type, "value", getattr(order_type, "name", str(order_type))).upper()
    assert value.endswith(expected)


def test_bridge_marks_error_as_rejected(monkeypatch):
    class ErrorClob(_StubClobRaw):
        def post_orders(self, orders):
            return [
                {
                    "errorMsg": "not enough balance / allowance",
                    "orderID": "",
                    "status": "",
                    "success": True,
                }
            ]

    raw = ErrorClob()

    class _Factory:
        def __call__(self, *args, **kwargs):
            return raw

    monkeypatch.setattr("py_clob_client.client.ClobClient", _Factory(), raising=True)

    rel = build_relayer(
        "real",
        base_url="https://clob.polymarket.com",
        private_key="0xabc",
        dry_run=False,
        chain_id=137,
    )
    ack = rel.place_orders([_order_request()])[0]
    assert not ack.accepted
    assert (ack.status or "").lower() == "rejected"
    assert ack.order_id == ""
