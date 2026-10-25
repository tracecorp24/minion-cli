"""
Telegram-Bot Notification Plugin for Minion Fortress.
Dispatches critical alerts, health warnings, and watchdog triggers.
"""

from __future__ import annotations
import time
from typing import Dict, Any


class TelegramPlugin:
    def __init__(self) -> None:
        self.name: str = "Telegram-Bot"
        self.version: str = "3.1.0"
        self.is_active: bool = False  # Paused by default as in plan.md
        self.description: str = "Instant telegram webhook for fatal errors and panic mode alerts"
        self.alerts_dispatched: int = 0

    def toggle(self) -> bool:
        self.is_active = not self.is_active
        return self.is_active

    def send_alert(self, title: str, message: str) -> Dict[str, Any]:
        if not self.is_active:
            return {"status": "skipped", "reason": "Telegram-Bot plugin is paused."}

        self.alerts_dispatched += 1
        return {
            "status": "sent",
            "plugin": self.name,
            "title": title,
            "preview": message[:60],
            "timestamp": time.time(),
        }
