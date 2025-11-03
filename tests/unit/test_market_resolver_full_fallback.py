from polybot.adapters.polymarket.market_resolver import PyClobMarketSearcher


class _StubPyClobFullOnly:
    def get_simplified_markets(self, cursor=None):
        return {"data": [], "next_cursor": "LTE="}

    def get_markets(self):
        return {
            "data": [
                {
                    "question": "Will Coinbase list HYPE in 2025?",
                    "condition_id": "cond-9",
                    "tokens": [
                        {"name": "Yes", "token_id": "YES9"},
                        {"name": "No", "token_id": "NO9"},
                    ],
                }
            ]
        }
    def get_market(self, condition_id):
        # Return matching market when hydrating
        return {
            "question": "Will Coinbase list HYPE in 2025?",
            "tokens": [
                {"name": "Yes", "token_id": "YES9"},
                {"name": "No", "token_id": "NO9"},
            ],
        }


def test_search_by_query_falls_back_to_full_markets():
    s = PyClobMarketSearcher(_StubPyClobFullOnly())
    res = s.search_by_query("coinbase hype", limit=3)
    assert res and res[0].market_id == "cond-9"
