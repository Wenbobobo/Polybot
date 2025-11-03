from polybot.adapters.polymarket.market_resolver import PyClobMarketSearcher, choose_outcome


class _StubPyClob:
    def __init__(self):
        pass

    def get_simplified_markets(self, cursor=None):
        # minimal shape: question + condition_id
        return {
            "data": [
                {"question": "Will Coinbase list HYPE in 2025?", "condition_id": "cond-1"},
                {"question": "Unrelated market", "condition_id": "cond-2"},
            ],
            "next_cursor": "LTE=",
        }

    def get_market(self, condition_id):
        if condition_id == "cond-1":
            return {
                "question": "Will Coinbase list HYPE in 2025?",
                "tokens": [
                    {"name": "Yes", "token_id": "YES_TOKEN"},
                    {"name": "No", "token_id": "NO_TOKEN"},
                ],
            }
        return {"question": "Unrelated", "tokens": []}


def test_pyclob_search_by_query_and_choose_outcome():
    s = PyClobMarketSearcher(_StubPyClob())
    res = s.search_by_query("hype coinbase list", limit=3)
    assert res and res[0].market_id == "cond-1"
    sel = choose_outcome(res[0].outcomes, prefer="yes")
    assert sel and sel.outcome_id == "YES_TOKEN"

