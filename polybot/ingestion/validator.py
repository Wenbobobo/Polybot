from __future__ import annotations

from typing import Dict, Any, Tuple
from pydantic import ValidationError

from polybot.adapters.polymarket.schemas import SnapshotMsg, DeltaMsg


def validate_message(msg: Dict[str, Any]) -> Tuple[bool, str]:
    t = msg.get("type")
    try:
        if t == "snapshot":
            SnapshotMsg(**msg)
        elif t == "delta":
            DeltaMsg(**msg)
        else:
            return False, f"unknown_type:{t}"
        return True, ""
    except ValidationError as e:
        return False, f"validation_error:{e.errors()[0]['loc']}"

