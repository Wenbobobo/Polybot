import json
from polybot.cli.commands import cmd_markets_resolve


def test_markets_resolve_debug_shows_ctor_error(monkeypatch):
    # Force client construction to raise
    monkeypatch.setattr("polybot.cli.commands._make_pyclob_client", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("ctor_failed")), raising=True)
    out = cmd_markets_resolve(url="https://polymarket.com/event/x", prefer="yes", as_json=True, debug=True)
    data = json.loads(out)
    assert data and data[0]["debug"]["client_ctor_error"].find("ctor_failed") >= 0

