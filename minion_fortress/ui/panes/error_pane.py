"""
Feature 2: Error & Health Monitor Pane (Özellik 2: Error & Health Monitor Penceresi)
Collects exceptions, HTTP 429/500 errors, RAM/CPU thresholds, and Watchdog Auto-Healing events.
"""

from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from rich.text import Text

from minion_fortress.core.state import FortressState, LogEntry
from minion_fortress.core.event_bus import EventBus, Event, EventType


class ErrorHealthPane(Vertical):
    """Monitors cluster-wide exceptions, status failures, and watchdog healing triggers."""

    def __init__(self, state: FortressState, event_bus: EventBus) -> None:
        super().__init__(classes="pane-container")
        self.state = state
        self.event_bus = event_bus
        self.error_count = 0
        self.warn_count = 0
        self.heal_count = 0

    def compose(self) -> ComposeResult:
        yield Static("🚨 ERROR & HEALTH MONITOR │ [SHIELD: ACTIVE]", classes="pane-title error-title", id="error-title")
        yield Static("Errors: 0 │ Warnings: 0 │ Auto-Heals: 0", id="error-telemetry-badge")
        yield RichLog(id="error-log-stream", classes="log-stream", highlight=True, markup=True)

    def on_mount(self) -> None:
        self.event_bus.subscribe(EventType.ERROR, self._handle_error_event)
        # Prepopulate with existing error logs if any
        log_view = self.query_one("#error-log-stream", RichLog)
        log_view.write("[bold yellow][SYSTEM][/bold yellow] Auto-Healing Watchdog armed (5s heartbeat threshold).")
        for entry in self.state.error_logs.get_recent(15):
            self._render_log_entry(entry)

    def _handle_error_event(self, event: Event) -> None:
        import time
        data = event.data
        level = data.get("level", "ERROR").upper()
        source = data.get("source", "system")
        message = data.get("message", "")
        entry = LogEntry(
            timestamp=event.data.get("timestamp_str") or time.strftime("%H:%M:%S"),
            level=level,
            source=source,
            message=message,
        )
        import threading
        if threading.current_thread() is threading.main_thread():
            self._render_log_entry(entry)
        else:
            self.app.call_from_thread(self._render_log_entry, entry)

    def _render_log_entry(self, entry: LogEntry) -> None:
        try:
            log_view = self.query_one("#error-log-stream", RichLog)
            lvl = entry.level.upper()

            if "HEAL" in lvl:
                self.heal_count += 1
                prefix = "[bold green][AUTO-HEAL][/bold green]"
                style = "green"
            elif "FATAL" in lvl:
                self.error_count += 1
                prefix = "[bold red][FATAL][/bold red]"
                style = "bold red"
            elif "ERROR" in lvl:
                self.error_count += 1
                prefix = "[red][ERROR][/red]"
                style = "red"
            else:
                self.warn_count += 1
                prefix = "[yellow][WARN][/yellow]"
                style = "yellow"

            text = Text.assemble(
                (f"[{entry.timestamp or 'LIVE'}] ", "dim"),
                Text.from_markup(f"{prefix} "),
                (f"({entry.source}) ", "bold white"),
                (entry.message, style),
            )
            log_view.write(text)

            badge = self.query_one("#error-telemetry-badge", Static)
            badge.update(f"Errors: {self.error_count} │ Warnings: {self.warn_count} │ Auto-Heals: {self.heal_count}")
        except Exception:
            pass
