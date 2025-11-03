from polybot.cli.commands import cmd_markets_sync


class _StubGamma:
    def __init__(self, markets):
        self._m = markets

    def list_markets(self):
        return self._m


class _StubClob:
    def __init__(self, tokens):
        self._t = tokens  # dict condition_id -> tokens list

    def get_market(self, condition_id):
        return {"question": "Q", "tokens": self._t.get(condition_id, [])}


def test_cmd_markets_sync_once_enriches(monkeypatch, tmp_path):
    # Prepare stub data
    gamma_markets = [
        {
            "market_id": "condX",
            "title": "Q",
            "status": "active",
            "outcomes": [
                {"outcome_id": "o1", "name": "Yes"},
                {"outcome_id": "o2", "name": "No"},
            ],
        }
    ]
    clob_tokens = {
        "condX": [
            {"name": "Yes", "token_id": "YES_X"},
            {"name": "No", "token_id": "NO_X"},
        ]
    }

    # Monkeypatch GammaHttpClient and make_pyclob_client used in command
    monkeypatch.setattr(
        "polybot.cli.commands.GammaHttpClient",
        lambda base_url, client=None: _StubGamma(gamma_markets),
        raising=True,
    )
    def _sync_markets_stub(con, ghc, cl, clob_max_pages=2):
        return {"gamma_count": len(gamma_markets), "enriched": 1, "source": "gamma"}

    monkeypatch.setattr("polybot.cli.commands.sync_markets", _sync_markets_stub, raising=True)

    db = f"sqlite:///{(tmp_path/'ms.db').as_posix()}"
    out = cmd_markets_sync(db_url=db, gamma_base_url="https://gamma", use_pyclob=True, once=True)
    assert "markets_sync" in out and "gamma=1" in out and "enriched=1" in out
