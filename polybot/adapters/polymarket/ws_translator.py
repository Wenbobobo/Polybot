from __future__ import annotations

from typing import Any, Dict, Optional


def translate_polymarket_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Translate Polymarket-like WS messages to internal snapshot/delta.

    Supports:
    - {"type": "l2_snapshot", "seq": int, "bids": [...], "asks": [...]} -> snapshot
    - {"type": "l2_update", "seq": int, "bids": [...], "asks": [...]} -> delta
    - Passthrough for {"type": "snapshot"|"delta", ...}
    Returns None if message type is not recognized.
    """
    # Some payloads may wrap the actual L2 fields under a `data` key
    base: Dict[str, Any] = msg.get("data") if isinstance(msg.get("data"), dict) else msg
    t = base.get("type", msg.get("type"))
    if t == "snapshot" or t == "delta":
        return base
    if t == "l2_snapshot":
        out = {
            "type": "snapshot",
            "seq": int(base.get("seq", 0)),
            "bids": base.get("bids", []),
            "asks": base.get("asks", []),
        }
        # Copy optional metadata if present
        for k in ("market", "channel", "ts_ms"):
            if k in msg:
                out[k] = msg[k]
            elif k in base:
                out[k] = base[k]
        return out
    if t == "l2_update":
        out: Dict[str, Any] = {
            "type": "delta",
            "seq": int(base.get("seq", 0)),
            "bids": base.get("bids", []),
            "asks": base.get("asks", []),
        }
        if "checksum" in msg:
            out["checksum"] = msg["checksum"]
        elif "checksum" in base:
            out["checksum"] = base["checksum"]
        for k in ("market", "channel", "ts_ms"):
            if k in msg:
                out[k] = msg[k]
            elif k in base:
                out[k] = base[k]
        return out
    return None
