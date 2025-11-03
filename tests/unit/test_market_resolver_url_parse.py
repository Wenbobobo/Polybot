from polybot.adapters.polymarket.market_resolver import parse_polymarket_url


def test_parse_polymarket_url_with_tid():
    url = "https://polymarket.com/event/will-coinbase-list-hype-in-2025/will-coinbase-list-hype-in-2025?tid=1762100517211"
    meta = parse_polymarket_url(url)
    assert meta["slug"].startswith("will-coinbase-list-hype")
    assert meta["tid"] == "1762100517211"


def test_parse_polymarket_url_no_tid():
    url = "https://polymarket.com/event/sample-market"
    meta = parse_polymarket_url(url)
    assert meta["slug"] == "sample-market"
    assert meta["tid"] is None

