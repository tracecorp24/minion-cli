"""
Feature 6 & Minion View: Live Minion Pane and Time Travel Replay.
Displays ASCII Minion avatar, progress bar, telemetry, and allows rewinding
up to 50 historical steps using ring buffer snapshots.
"""

from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import Static, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual import on
from rich.text import Text

from minion_fortress.core.state import FortressState, MinionState, MinionStatus, LogEntry
from minion_fortress.core.event_bus import EventBus, Event, EventType


def render_progress_bar(progress: int, width: int = 15) -> str:
    filled = int(width * (progress / 100.0))
    empty = width - filled
    return "█" * filled + "░" * empty


class MinionPane(Vertical):
    """Minion inspection pane featuring live logs and time travel history rewind."""

    def __init__(self, state: FortressState, event_bus: EventBus, initial_minion_id: str = "01") -> None:
        super().__init__(classes="pane-container")
        self.state = state
        self.event_bus = event_bus
        self.selected_minion_id = initial_minion_id
        self.is_replay_mode: bool = False
        self.replay_offset: int = 0

    def compose(self) -> ComposeResult:
        yield Static(f"🍌 MINION-{self.selected_minion_id} [ast-parser]", classes="pane-title", id="minion-pane-title")
        yield Static("", id="minion-ascii-box", classes="minion-avatar-box")

        with Horizontal(classes="action-bar", id="time-travel-bar"):
            yield Static("⏪ Time Travel: ", id="tt-label")
            yield Button("◀ -1", id="btn-replay-prev")
            yield Button("+1 ▶", id="btn-replay-next")
            yield Button("-10", id="btn-replay-10")
            yield Button("Replay 50", id="btn-replay-50")
            yield Button("🔴 Live Stream", id="btn-live", classes="active-btn")

        yield RichLog(id="minion-log-stream", classes="log-stream", highlight=True, markup=True)

    def on_mount(self) -> None:
        self.event_bus.subscribe(EventType.LOG, self._on_log)
        self.event_bus.subscribe(EventType.STATUS_CHANGE, self._on_status_change)
        self.refresh_minion_display()

    def set_minion(self, minion_id: str) -> None:
        """Switches active minion focus."""
        if minion_id in self.state.minions:
            self.selected_minion_id = minion_id
            self.is_replay_mode = False
            self.replay_offset = 0
            self.refresh_minion_display()

    def refresh_minion_display(self) -> None:
        """Updates the avatar, progress bar, and log view for the selected minion."""
        minion = self.state.minions.get(self.selected_minion_id)
        if not minion:
            return

        # Update title
        mode_tag = f" [⏪ REPLAY: -{self.replay_offset}]" if self.is_replay_mode else " [LIVE]"
        title = self.query_one("#minion-pane-title", Static)
        title.update(f"🍌 MINION-{minion.id} [{minion.name}] ({minion.model}){mode_tag}")

        # Update ASCII Art box
        pbar = render_progress_bar(minion.progress, width=12)
        avatar_text = (
            f"  (o) > {minion.current_task}\n"
            f" |█| > [PROGRESS] [{pbar}] {minion.progress}%\n"
            f"  / \\ > Status: {minion.status.value} │ CPU: {minion.cpu}% │ RAM: {minion.memory_mb}MB"
        )
        ascii_box = self.query_one("#minion-ascii-box", Static)
        ascii_box.update(avatar_text)

        # Refresh logs
        log_view = self.query_one("#minion-log-stream", RichLog)
        log_view.clear()

        if self.is_replay_mode:
            replay_entries = minion.logs.replay(self.replay_offset)
            log_view.write(f"[bold yellow]=== ⏪ TIME TRAVEL PLAYBACK: LAST {len(replay_entries)} STEPS ===[/bold yellow]")
            for entry in replay_entries:
                log_view.write(f"[{entry.timestamp}] [{entry.level}] {entry.message}")
        else:
            recent_entries = minion.logs.get_recent(40)
            for entry in recent_entries:
                log_view.write(f"[{entry.timestamp}] [{entry.level}] {entry.message}")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        minion = self.state.minions.get(self.selected_minion_id)
        if not minion:
            return

        if btn_id == "btn-replay-prev":
            self.is_replay_mode = True
            self.replay_offset = min(len(minion.logs), self.replay_offset + 1)
            self._update_button_styles()
            self.refresh_minion_display()
        elif btn_id == "btn-replay-next":
            self.replay_offset = max(0, self.replay_offset - 1)
            if self.replay_offset == 0:
                self.is_replay_mode = False
            self._update_button_styles()
            self.refresh_minion_display()
        elif btn_id == "btn-replay-10":
            self.is_replay_mode = True
            self.replay_offset = min(len(minion.logs), 10)
            self._update_button_styles()
            self.refresh_minion_display()
        elif btn_id == "btn-replay-50":
            self.is_replay_mode = True
            self.replay_offset = min(len(minion.logs), 50)
            self._update_button_styles()
            self.refresh_minion_display()
        elif btn_id == "btn-live":
            self.is_replay_mode = False
            self.replay_offset = 0
            self._update_button_styles()
            self.refresh_minion_display()

    def _update_button_styles(self) -> None:
        live_btn = self.query_one("#btn-live", Button)
        if self.is_replay_mode:
            live_btn.classes = ""
        else:
            live_btn.classes = "active-btn"

    def _on_log(self, event: Event) -> None:
        data = event.data
        if data.get("minion_id") == self.selected_minion_id:
            if not self.is_replay_mode:
                self.app.call_from_thread(self.refresh_minion_display)

    def _on_status_change(self, event: Event) -> None:
        self.app.call_from_thread(self.refresh_minion_display)
