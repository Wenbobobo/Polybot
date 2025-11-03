from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


_URL_RE = re.compile(r"https?://[^/]+/(?:event|market)/(?P<slug>[^?\s#]+)(?:[^?\s#]*)?(?:\?.*?tid=(?P<tid>\d+))?", re.I)


@dataclass
class OutcomeInfo:
    outcome_id: str
    name: str


@dataclass
class MarketInfo:
    market_id: str  # a.k.a. condition_id
    title: str
    outcomes: List[OutcomeInfo]


def parse_polymarket_url(url: str) -> Dict[str, Optional[str]]:
    """Parse a Polymarket URL to extract slug and tid when present.

    Returns {"slug": str|None, "tid": str|None}.
    """
    m = _URL_RE.search(url or "")
    if not m:
        return {"slug": None, "tid": None}
    return {"slug": m.group("slug"), "tid": m.group("tid")}


class PyClobMarketSearcher:
    """Searcher using py-clob-client to find markets and outcomes.

    Expects a client exposing get_simplified_markets(cursor=None) and get_market(condition_id).
    """

    def __init__(self, client: Any):
        self.client = client

    def _iter_simplified_markets(self, max_pages: int = 10) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        pages = 0
        while pages < max_pages:
            if cursor:
                res = self.client.get_simplified_markets(cursor)
            else:
                res = self.client.get_simplified_markets()
            data = res.get("data") or []
            out.extend(data)
            cursor = res.get("next_cursor") or res.get("next") or None
            pages += 1
            if not cursor or cursor in ("", "LTE="):
                break
        return out

    @staticmethod
    def _match_score(question: str, needle: str) -> int:
        q = (question or "").lower()
        n = (needle or "").lower()
        if n in q:
            return len(n)
        # split words and count overlaps
        qwords = set(re.split(r"\W+", q))
        nwords = set(re.split(r"\W+", n))
        return len(qwords & nwords)

    def search_by_query(self, query: str, limit: int = 5) -> List[MarketInfo]:
        sims = self._iter_simplified_markets()
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for m in sims:
            score = self._match_score(str(m.get("question") or m.get("title") or ""), query)
            if score > 0:
                scored.append((score, m))
        scored.sort(key=lambda x: (-x[0], str(x[1].get("question") or "")))
        top = [m for _, m in scored[: max(1, limit)]]
        return [self._hydrate_market(mi) for mi in top]

    def search_by_url(self, url: str, limit: int = 5) -> List[MarketInfo]:
        meta = parse_polymarket_url(url)
        slug = meta.get("slug") or ""
        if not slug:
            return []
        query = slug.replace("-", " ")
        return self.search_by_query(query, limit=limit)

    def _hydrate_market(self, simplified: Dict[str, Any]) -> MarketInfo:
        # Use condition_id to fetch full details
        cond = str(simplified.get("condition_id") or simplified.get("id") or simplified.get("market"))
        details = self.client.get_market(cond)
        title = str(details.get("question") or details.get("title") or simplified.get("question") or "")
        outs: List[OutcomeInfo] = []
        tokens = details.get("tokens") or []
        for t in tokens:
            name = str(t.get("name") or t.get("symbol") or t.get("displayName") or "")
            tok = str(t.get("token_id") or t.get("tokenId") or t.get("id") or "")
            outs.append(OutcomeInfo(outcome_id=tok, name=name))
        return MarketInfo(market_id=cond, title=title, outcomes=outs)


def choose_outcome(outcomes: List[OutcomeInfo], prefer: Optional[str] = None) -> Optional[OutcomeInfo]:
    if not outcomes:
        return None
    if prefer:
        p = prefer.strip().lower()
        for o in outcomes:
            if o.name.strip().lower() == p:
                return o
    # Fallbacks: try Yes/No heuristic
    for key in ("yes", "no"):
        for o in outcomes:
            if o.name.strip().lower() == key:
                return o
    return outcomes[0]

