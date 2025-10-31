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
    t = msg.get("type")
    if t == "snapshot" or t == "delta":
        return msg
    if t == "l2_snapshot":
        return {
            "type": "snapshot",
            "seq": int(msg.get("seq", 0)),
            "bids": msg.get("bids", []),
            "asks": msg.get("asks", []),
        }
    if t == "l2_update":
        out: Dict[str, Any] = {
            "type": "delta",
            "seq": int(msg.get("seq", 0)),
            "bids": msg.get("bids", []),
            "asks": msg.get("asks", []),
        }
        if "checksum" in msg:
            out["checksum"] = msg["checksum"]
        return out
    return None

