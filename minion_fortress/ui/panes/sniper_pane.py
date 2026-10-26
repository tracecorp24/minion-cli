"""
Feature 3: Custom Log Sniper Pane (Özellik 3: 🔍 Özel Log Sniper Penceresi)
Provides real-time regex pattern matching and live highlighting across
thousands of cluster log entries with zero latency.
"""

from __future__ import annotations
import re
from textual.app import ComposeResult
from textual.widgets import Static, Input, RichLog
from textual.containers import Vertical
from rich.text import Text

from minion_fortress.core.state import FortressState, LogEntry
from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.ui.cli_input import CliCommandInput


class LogSniperPane(Vertical):
    """Regex sniper pane that filters and highlights matching log lines instantaneously."""

    def __init__(self, state: FortressState, event_bus: EventBus) -> None:
        super().__init__(classes="pane-container")
        self.state = state
        self.event_bus = event_bus
        self.current_pattern: str = ""
        self.match_count: int = 0

    def compose(self) -> ComposeResult:
        yield Static("🔍 CUSTOM LOG SNIPER (Live Regex Filter)", classes="pane-title sniper-title")
        yield CliCommandInput(
            placeholder="Regex pattern (e.g. [ERROR|429|AST|timeout])...",
            id="sniper-regex-input",
        )
        yield Static("Matches: 0 │ Filter: (none - showing all logs)", id="sniper-status-bar")
        yield RichLog(id="sniper-log-stream", classes="log-stream", highlight=True, markup=True)

    def on_mount(self) -> None:
        self.event_bus.subscribe(EventType.LOG, self._handle_new_log)
        self.event_bus.subscribe(EventType.ERROR, self._handle_new_log)
        self._refilter_all()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Triggers live instantaneous re-filtering as the user types."""
        self.current_pattern = event.value.strip()
        self._refilter_all()

    def _handle_new_log(self, event: Event) -> None:
        """Processes incoming real-time logs against active regex pattern."""
        import time
        data = event.data
        entry = LogEntry(
            timestamp=data.get("timestamp_str") or time.strftime("%H:%M:%S"),
            level=data.get("level", "INFO"),
            source=data.get("source", "system"),
            message=data.get("message", ""),
        )
        import threading
        if threading.current_thread() is threading.main_thread():
            self._check_and_append_log(entry)
        else:
            self.app.call_from_thread(self._check_and_append_log, entry)

    def _check_and_append_log(self, entry: LogEntry) -> None:
        try:
            line_str = f"[{entry.timestamp or 'LIVE'}] [{entry.level}] ({entry.source}) {entry.message}"
            log_view = self.query_one("#sniper-log-stream", RichLog)

            if not self.current_pattern:
                # Normal append
                log_view.write(line_str)
                return

            try:
                regex = re.compile(self.current_pattern, re.IGNORECASE)
                if regex.search(line_str):
                    self.match_count += 1
                    styled_text = self._highlight_matches(line_str, regex)
                    log_view.write(styled_text)
                    self._update_status()
            except re.error:
                # Invalid regex during typing
                pass
        except Exception:
            pass

    def _refilter_all(self) -> None:
        """Re-scans state ring buffer with the current regex."""
        try:
            log_view = self.query_one("#sniper-log-stream", RichLog)
            log_view.clear()
            self.match_count = 0

            entries = self.state.global_logs.get_recent(200)

            if not self.current_pattern:
                for entry in entries[-40:]:
                    line_str = f"[{entry.timestamp}] [{entry.level}] ({entry.source}) {entry.message}"
                    log_view.write(line_str)
                self._update_status()
                return

            try:
                regex = re.compile(self.current_pattern, re.IGNORECASE)
                for entry in entries:
                    line_str = f"[{entry.timestamp}] [{entry.level}] ({entry.source}) {entry.message}"
                    if regex.search(line_str):
                        self.match_count += 1
                        styled_text = self._highlight_matches(line_str, regex)
                        log_view.write(styled_text)
            except re.error:
                log_view.write("[yellow]⚠️ Invalid regex pattern syntax[/yellow]")

            self._update_status()
        except Exception:
            pass

    def _highlight_matches(self, line: str, regex: re.Pattern) -> Text:
        """Highlights matching regex tokens with high-visibility Minion gold."""
        text = Text()
        last_idx = 0
        for m in regex.finditer(line):
            start, end = m.span()
            if start > last_idx:
                text.append(line[last_idx:start])
            text.append(line[start:end], style="bold black on #FFE135")
            last_idx = end
        if last_idx < len(line):
            text.append(line[last_idx:])
        return text

    def _update_status(self) -> None:
        try:
            bar = self.query_one("#sniper-status-bar", Static)
            if self.current_pattern:
                bar.update(f"Matches: {self.match_count} │ Filter: [bold yellow]/{self.current_pattern}/[/bold yellow]")
            else:
                bar.update(f"Matches: {self.match_count} │ Filter: (none - showing live stream)")
        except Exception:
            pass
