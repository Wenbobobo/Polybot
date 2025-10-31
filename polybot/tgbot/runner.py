from __future__ import annotations

from typing import Dict, Any

from .agent import BotAgent, BotContext


class TelegramUpdateRunner:
    """Minimal runner to handle Telegram-like updates (offline simulation).

    Expected update format: {"message": {"text": "..."}}
    """

    def __init__(self, agent: BotAgent):
        self.agent = agent

    def handle_update(self, update: Dict[str, Any]) -> str:
        msg = update.get("message") or {}
        text = msg.get("text", "")
        return self.agent.handle_text(text)

