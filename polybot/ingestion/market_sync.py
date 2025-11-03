from __future__ import annotations

from typing import Protocol, List, Dict, Any, Optional
import sqlite3

from polybot.storage.markets import upsert_markets


class GammaClientProto(Protocol):
    def list_markets(self) -> List[Dict[str, Any]]: ...


class ClobClientProto(Protocol):
    def get_market(self, condition_id: str) -> Dict[str, Any]: ...
    def get_simplified_markets(self, cursor: Optional[str] = None) -> Dict[str, Any]: ...


def enrich_markets_with_clob_tokens(markets: List[Dict[str, Any]], clob: ClobClientProto) -> int:
    """Enrich markets' outcomes with token_id via CLOB get_market(condition_id).

    Returns number of markets enriched.
    """
    enriched = 0
    for m in markets:
        cond = m.get("condition_id") or m.get("market_id") or m.get("id")
        if not cond:
            continue
        try:
            details = clob.get_market(str(cond))
        except Exception:
            continue
        tokens = details.get("tokens") or []
        if not tokens:
            continue
        # Build mapping by token name to token_id
        tmap = {}
        for t in tokens:
            name = str(t.get("name") or t.get("symbol") or t.get("displayName") or "").strip()
            tok = str(t.get("token_id") or t.get("tokenId") or t.get("id") or "").strip()
            if tok:
                tmap[name.lower()] = tok
        outs = m.get("outcomes") or []
        out_new: List[Dict[str, Any]] = []
        changed = False
        for o in outs:
            name = str(o.get("name", "")).strip()
            oid = o.get("outcome_id")
            # Prefer token id from CLOB if available
            tok = tmap.get(name.lower())
            if tok and tok != oid:
                changed = True
                out_new.append({"outcome_id": tok, "name": name, **{k: v for k, v in o.items() if k not in ("outcome_id", "name")}})
            else:
                out_new.append(o)
        if changed:
            m["outcomes"] = out_new
            enriched += 1
    return enriched


def _is_condition_like(val: Optional[str]) -> bool:
    if not val:
        return False
    s = str(val)
    return s.startswith("0x") and len(s) >= 18 and all(c in "0123456789abcdefABCDEFx" for c in s[:])


def sync_markets(
    con: sqlite3.Connection,
    gamma: GammaClientProto,
    clob: Optional[ClobClientProto] = None,
    clob_max_pages: int = 2,
    clob_page_limit: int = 50,
    clob_details_limit: int = 10,
) -> Dict[str, int]:
    """Fetch markets from Gamma and optionally enrich outcomes with token IDs via CLOB.

    Persists to DB and returns stats dict.
    """
    markets = gamma.list_markets()
    stats = {"gamma_count": len(markets), "enriched": 0, "source": "gamma"}
    # If gamma lacks usable identifiers, optionally fall back to CLOB discovery
    def _has_condition_id(ms: List[Dict[str, Any]]) -> bool:
        for m in ms:
            cid = m.get("condition_id") or m.get("market_id")
            if _is_condition_like(cid):
                return True
        return False
    if (not markets or not _has_condition_id(markets)) and clob is not None:
        try:
            markets = clob_discover_markets(
                clob,
                max_pages=clob_max_pages,
                page_limit=clob_page_limit,
                details_limit=clob_details_limit,
            )
            stats["source"] = "clob"
        except Exception:
            pass
    if clob is not None:
        try:
            stats["enriched"] = enrich_markets_with_clob_tokens(markets, clob)
        except Exception:
            stats["enriched"] = 0
    upsert_markets(con, markets)
    return stats


def clob_discover_markets(
    clob: ClobClientProto,
    max_pages: int = 10,
    page_limit: int = 50,
    details_limit: int = 10,
) -> List[Dict[str, Any]]:
    """Discover markets via CLOB client (simplified + details) and normalize.

    Returns a list of normalized dicts with market_id=condition_id, title=question,
    and outcomes derived from tokens.
    """
    out: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    pages = 0
    details_calls = 0
    while pages < max_pages:
        try:
            res = clob.get_simplified_markets(cursor) if cursor else clob.get_simplified_markets()
        except Exception:
            break
        data = res.get("data") or []
        for m in data:
            cond = str(m.get("condition_id") or m.get("id") or "").strip()
            title = str(m.get("question") or m.get("title") or "").strip()
            if not cond:
                continue
            # Prefer clobTokenIds + outcomes from simplified to avoid per-market details call
            tokens: List[Dict[str, Any]] = []
            cti = m.get("clobTokenIds")
            outs_names = m.get("outcomes") if isinstance(m.get("outcomes"), list) else []
            if isinstance(cti, str) and cti.strip() and outs_names:
                toks = [x.strip() for x in cti.split(",") if x.strip()]
                if len(toks) == len(outs_names):
                    for i, tok in enumerate(toks):
                        tokens.append({"token_id": tok, "name": outs_names[i]})
            # Fallback to per-market details if we still lack tokens and under budget
            if not tokens and details_calls < details_limit:
                try:
                    details = clob.get_market(cond)
                    tokens = details.get("tokens") or []
                    details_calls += 1
                except Exception:
                    tokens = []
            outs: List[Dict[str, Any]] = []
            for t in tokens:
                if not isinstance(t, dict):
                    continue
                oid = t.get("token_id") or t.get("tokenId") or t.get("id")
                name = t.get("name") or t.get("symbol") or t.get("displayName") or ""
                outs.append({"outcome_id": str(oid or ""), "name": str(name)})
            out.append({
                "market_id": cond,
                "title": title,
                "status": "active",
                "outcomes": outs,
            })
        cursor = res.get("next_cursor") or res.get("next") or None
        pages += 1
        if not cursor or cursor in ("", "LTE="):
            break
    return out
