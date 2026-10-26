"""
MINION-FORTRESS (KOVAN-X) v3.0: Detached Window Node.
Independent dedicated window node connected via IPC socket.
Displays dedicated error streams, cluster health alerts, and live minion feed.
"""

from __future__ import annotations
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, RichLog, Input
from rich.text import Text

DETACHED_CSS = """
Screen {
    background: #0f0f0f;
    color: #e0e0e0;
}

#detached-banner {
    background: #FFE135;
    color: #000000;
    text-style: bold;
    height: 1;
    content-align: center middle;
}

#status-badge {
    background: #1a1a1a;
    color: #00ff88;
    height: 1;
    padding-left: 1;
}

.pane-box {
    border: round #FFE135;
    height: 1fr;
    background: #141414;
    margin: 0 1;
}

.pane-title {
    background: #FFE135;
    color: #000000;
    text-style: bold;
    padding-left: 1;
    height: 1;
}

.error-title {
    background: #FF3344;
    color: #ffffff;
}

.stream-log {
    height: 1fr;
    background: #101010;
}

#cmd-bar {
    dock: bottom;
    background: #1a1a1a;
    border-top: solid #FFE135;
    height: 3;
}
"""


class DetachedMonitorApp(App):
    """Independent second window node for Fortress monitoring."""

    CSS = DETACHED_CSS
    TITLE = "🍌 MINION-FORTRESS: DETACHED MONITOR NODE"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Close Monitor", priority=True),
        Binding("f12", "quick_banana", "🍌 Panic", priority=True),
    ]

    def __init__(self, host: str = "127.0.0.1", port: int = 42010, target_cli: str = "all") -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.target_cli = target_cli
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._connected: bool = False
        self._running: bool = True
        self._error_count = 0
        self._event_count = 0

    def compose(self) -> ComposeResult:
        banner_tag = f"[{self.target_cli.upper()}]" if self.target_cli != "all" else "[TÜM SİSTEM]"
        yield Static(f" 🍌 MINION-FORTRESS: AYRILMIŞ CLI DÜĞÜMÜ {banner_tag} - ZERO-LAG IPC LINK ", id="detached-banner")
        yield Static("• Status: Connecting to Main Fortress Daemon...", id="status-badge")

        with Horizontal():
            # Left Half: Dedicated Live Error & Auto-Healing pane
            with Vertical(classes="pane-box"):
                yield Static("🚨 DEDICATED ERROR & HEALTH PANE", classes="pane-title error-title")
                yield RichLog(id="error-stream", classes="stream-log", highlight=True, markup=True)

            # Right Half: Live Activity & Telemetry Stream
            with Vertical(classes="pane-box"):
                yield Static(f"📡 LIVE EVENT STREAM {banner_tag}", classes="pane-title")
                yield RichLog(id="activity-stream", classes="stream-log", highlight=True, markup=True)

        ph = f"Send command to {self.target_cli} (e.g. pause, resume, banana, heal)..." if self.target_cli != "all" else "Send command to Main Fortress (e.g. banana, heal 01, @01 pause)..."
        with Horizontal(id="cmd-bar"):
            yield Input(placeholder=ph, id="remote-cmd-input")

        yield Footer()

    async def on_mount(self) -> None:
        asyncio.create_task(self._socket_client_loop())

    async def _socket_client_loop(self) -> None:
        """Maintains persistent loopback TCP connection to Fortress daemon."""
        status_bar = self.query_one("#status-badge", Static)
        error_log = self.query_one("#error-stream", RichLog)
        activity_log = self.query_one("#activity-stream", RichLog)

        while self._running:
            try:
                status_bar.update(f"• Status: Connecting to Fortress at {self.host}:{self.port}...")
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                self._connected = True
                status_bar.update("• Status: CONNECTED 🟢 [Live IPC Link Active]")
                activity_log.write("[bold green]✔ Synchronized with Minion-Fortress core daemon.[/bold green]")

                while self._running:
                    line = await self.reader.readline()
                    if not line:
                        break

                    try:
                        payload = json.loads(line.decode("utf-8").strip())
                        ev_type = payload.get("type", "LOG")
                        data = payload.get("data", {})
                        self._process_event(ev_type, data)
                    except Exception:
                        pass

            except (ConnectionRefusedError, OSError):
                self._connected = False
                status_bar.update("• Status: RECONNECTING 🟡 [Fortress daemon awaiting startup]")
                await asyncio.sleep(1.5)
            except Exception as e:
                self._connected = False
                status_bar.update(f"• Status: Disconnected ({e})")
                await asyncio.sleep(2.0)
            finally:
                if self.writer:
                    try:
                        self.writer.close()
                    except Exception:
                        pass
                    self.writer = None

    def _process_event(self, ev_type: str, data: dict) -> None:
        self._event_count += 1
        error_log = self.query_one("#error-stream", RichLog)
        activity_log = self.query_one("#activity-stream", RichLog)

        src = data.get("source", "system")
        lvl = data.get("level", "INFO")
        msg = data.get("message", "")
        ts = time.strftime("%H:%M:%S")

        # Route errors, auto-heals, and fatal warnings to Dedicated Error Pane
        if ev_type == "ERROR" or lvl in ("ERROR", "FATAL", "HEAL", "BANANA"):
            self._error_count += 1
            if "HEAL" in lvl:
                color = "green"
                prefix = "[bold green][HEAL][/bold green]"
            elif "FATAL" in lvl:
                color = "bold red"
                prefix = "[bold red][FATAL][/bold red]"
            elif "BANANA" in lvl:
                color = "bold #FFE135"
                prefix = "[bold #FFE135][BANANA][/bold #FFE135]"
            else:
                color = "red"
                prefix = "[red][ERROR][/red]"

            line = Text.assemble(
                (f"[{ts}] ", "dim"),
                Text.from_markup(f"{prefix} "),
                (f"({src}) ", "bold white"),
                (msg, color),
            )
            error_log.write(line)

        # Telemetry updates
        if ev_type == "TELEMETRY":
            tasks = f"{data.get('completed_tasks', 0)}/{data.get('total_tasks', 0)}"
            cost = f"${data.get('token_cost', 0):.4f}"
            activity_log.write(f"[{ts}] [cyan][TELEMETRY][/cyan] Tasks: {tasks} │ Cost: {cost} │ Active: {data.get('active_minions', 0)}")
        else:
            activity_log.write(f"[{ts}] [{lvl}] ({src}) {msg}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Sends remote command over IPC to main fortress."""
        cmd = event.value.strip()
        event.input.value = ""
        if not cmd:
            return

        # Auto-target minion if this window is attached to a specific minion
        if self.target_cli.startswith("minion-") and not cmd.startswith("@") and not cmd.lower().startswith("banana"):
            mid = self.target_cli.replace("minion-", "")
            cmd = f"@{mid} {cmd}"

        if self.writer:
            try:
                payload = json.dumps({"type": "COMMAND", "data": {"command": cmd, "source": f"detached_{self.target_cli}"}}).encode("utf-8") + b"\n"
                self.writer.write(payload)
                await self.writer.drain()
                activity_log = self.query_one("#activity-stream", RichLog)
                activity_log.write(f"[bold yellow]→ Dispatched remote command: {cmd}[/bold yellow]")
            except Exception as e:
                self.notify(f"Failed to send command: {e}", severity="error")
        else:
            self.notify("Not connected to main fortress daemon.", severity="warning")

    def action_quick_banana(self) -> None:
        if self.writer:
            payload = json.dumps({"type": "COMMAND", "data": {"command": "banana", "source": "detached_window"}}).encode("utf-8") + b"\n"
            self.writer.write(payload)
            self.notify("🍌 Emergency Banana Signal sent to core daemon!", severity="warning")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Minion Fortress Detached CLI Node")
    parser.add_argument("--target", type=str, default="all", help="Target CLI to attach to (e.g. minion-01, shell, error)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP")
    parser.add_argument("--port", type=int, default=42010, help="Socket port")
    args = parser.parse_args()

    app = DetachedMonitorApp(host=args.host, port=args.port, target_cli=args.target)
    app.run()


if __name__ == "__main__":
    main()
