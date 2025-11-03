from __future__ import annotations

import json
import time
from pathlib import Path

from polybot.cli.commands import (
    cmd_markets_sync,
    cmd_markets_resolve,
    cmd_markets_search,
    cmd_markets_show,
    cmd_relayer_live_order_from_config,
)


def _write(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def run(
    *,
    url: str,
    config_path: str,
    db_url: str = "sqlite:///./polybot.db",
    prefer: str = "yes",
    price: float = 0.01,
    size: float = 1.0,
    out_file: str = "recordings/hype_smoke.txt",
    timeout_s: float = 8.0,
) -> str:
    logs: list[str] = []
    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        logs.append(line)

    # 1) bounded sync: clob http only, with tight caps
    try:
        log("sync: gamma-only (no clob)")
        cmd_markets_sync(
            db_url=db_url,
            use_pyclob=False,
            use_clob_http=False,
            once=True,
            clob_max_pages=0,
            timeout_s=timeout_s,
        )
    except Exception as e:  # noqa: BLE001
        log(f"gamma-only error: {e}")
    try:
        log("sync: clob-http bounded")
        cmd_markets_sync(
            db_url=db_url,
            use_pyclob=False,
            use_clob_http=True,
            once=True,
            clob_max_pages=1,
            clob_details_limit=0,
            timeout_s=timeout_s,
        )
    except Exception as e:  # noqa: BLE001
        log(f"clob-http error: {e}")

    # 2) resolve via HTTP fallback (no details)
    log("resolve: http fallback --debug")
    resolved = cmd_markets_resolve(url=url, prefer=prefer, as_json=True, debug=True, http_timeout_s=timeout_s)
    logs.append(resolved)
    try:
        arr = json.loads(resolved)
    except Exception:
        arr = []
    market_id = ""
    outcome_id = ""
    if isinstance(arr, list) and arr:
        market_id = str(arr[0].get("market_id") or "")
        outcome_id = str(arr[0].get("selected_outcome_id") or "")
    if not market_id or not outcome_id:
        # fallback: try DB search on keywords
        log("fallback: DB search 'hyperliquid coinbase 2025'")
        try:
            q = cmd_markets_search(db_url=db_url, query="hyperliquid coinbase 2025", limit=5, as_json=True)
            qd = json.loads(q)
            if isinstance(qd, list) and qd:
                market_id = qd[0]["market_id"]
                show = cmd_markets_show(db_url=db_url, market_id=market_id, as_json=True)
                sd = json.loads(show)
                outs = sd.get("outcomes") or []
                # prefer Yes
                for o in outs:
                    if str(o.get("name","" )).lower() == prefer.lower():
                        outcome_id = o.get("outcome_id") or outcome_id
                        break
                if not outcome_id and outs:
                    outcome_id = outs[0].get("outcome_id") or ""
        except Exception as e:  # noqa: BLE001
            log(f"db-fallback error: {e}")

    if not market_id or not outcome_id:
        log("resolve failed: missing market_id/outcome_id")
        text = "\n".join(logs)
        _write(out_file, text)
        return text

    # 3) live order + close
    log(f"live buy: market={market_id} outcome={outcome_id}")
    buy = cmd_relayer_live_order_from_config(
        config_path,
        market_id=market_id,
        outcome_id=outcome_id,
        side="buy",
        price=price,
        size=size,
        confirm_live=True,
        as_json=True,
    )
    logs.append(buy)
    time.sleep(1)
    log("live sell (close)")
    sell = cmd_relayer_live_order_from_config(
        config_path,
        market_id=market_id,
        outcome_id=outcome_id,
        side="sell",
        price=price,
        size=size,
        confirm_live=True,
        as_json=True,
    )
    logs.append(sell)
    text = "\n".join(logs)
    _write(out_file, text)
    return text


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--db-url", default="sqlite:///./polybot.db")
    ap.add_argument("--prefer", default="yes")
    ap.add_argument("--price", type=float, default=0.01)
    ap.add_argument("--size", type=float, default=1.0)
    ap.add_argument("--out-file", default="recordings/hype_smoke.txt")
    ap.add_argument("--timeout-s", type=float, default=8.0)
    args = ap.parse_args()

    run(
        url=args.url,
        config_path=args.config,
        db_url=args.db_url,
        prefer=args.prefer,
        price=args.price,
        size=args.size,
        out_file=args.out_file,
        timeout_s=args.timeout_s,
    )

