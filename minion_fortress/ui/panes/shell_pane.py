"""
Interactive Shell CLI Pane for Minion Fortress.
Allows running OS shell commands, Python snippets, and fortress commands
with real-time streaming output inside a dedicated tile.
"""

from __future__ import annotations
import asyncio
import os
import sys
from textual.app import ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from rich.text import Text

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus, Event, EventType


class InteractiveShellPane(Vertical):
    """An interactive system and fortress shell pane with live command execution."""

    def __init__(self, state: FortressState, event_bus: EventBus) -> None:
        super().__init__(classes="pane-container shell-container")
        self.state = state
        self.event_bus = event_bus

    def compose(self) -> ComposeResult:
        yield Static("💻 INTERACTIVE SHELL CLI (System & Fortress Console)", classes="pane-title shell-title")
        yield RichLog(id="shell-stream", classes="log-stream", highlight=True, markup=True)

    def on_mount(self) -> None:
        log = self.query_one("#shell-stream", RichLog)
        cwd = os.getcwd()
        py_ver = sys.version.split()[0]
        banner = (
            f"[bold #00FF7F]Minion-Fortress Shell v3.0[/bold #00FF7F] (Python {py_ver})\n"
            f"[dim]Working directory: {cwd}[/dim]\n"
            f"[cyan]Type any system command (dir, ping, ipconfig, python), or fortress commands (banana, @01 pause, export, help).[/cyan]\n"
        )
        log.write(banner)

    async def execute_command(self, cmd_str: str) -> None:
        """Executes a command and writes output to the shell stream."""
        log = self.query_one("#shell-stream", RichLog)
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return

        log.write(f"\n[bold #FFE135]shell>[/bold #FFE135] [white]{cmd_str}[/white]")

        # Check for built-in quick commands
        if cmd_str.lower() in ("clear", "cls"):
            log.clear()
            return

        if cmd_str.lower() in ("help", "?"):
            help_text = (
                "[bold cyan]Kullanılabilir Shell Komutları:[/bold cyan]\n"
                "• [yellow]Sistem Komutları:[/yellow] dir, cls, echo, ping, ipconfig, git status, python...\n"
                "• [yellow]Fortress Komutları:[/yellow] @01 pause, @01 resume, banana, heal 01, export, detach\n"
                "• [yellow]clear / cls:[/yellow] Terminal ekranını temizler"
            )
            log.write(help_text)
            return

        # Check if it's a fortress direct command (starts with @, or banana, heal, etc.)
        tokens = cmd_str.split()
        if tokens[0].startswith("@") or tokens[0].lower() in ("banana", "heal", "export", "detach", "spawn"):
            # Dispatch event to EventBus for Fortress app
            await self.event_bus.publish(
                Event(
                    type=EventType.COMMAND,
                    source="shell_pane",
                    data={"command": cmd_str},
                )
            )
            log.write(f"[dim green]✔ Komut Fortress Core EventBus'a iletildi: {cmd_str}[/dim green]")
            return

        # Otherwise execute as subprocess shell command
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if stdout:
                # Decode with fallback
                out_txt = stdout.decode("utf-8", errors="replace").strip()
                if out_txt:
                    log.write(out_txt)

            if stderr:
                err_txt = stderr.decode("utf-8", errors="replace").strip()
                if err_txt:
                    log.write(f"[bold red]{err_txt}[/bold red]")

            if proc.returncode != 0:
                log.write(f"[dim red]Process exited with code {proc.returncode}[/dim red]")
            else:
                log.write("[dim green]✔ Başarılı (Exit code 0)[/dim green]")

        except Exception as e:
            log.write(f"[bold red]Hata:[/bold red] {e}")
