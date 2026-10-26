"""
Interactive Shell CLI Pane for Minion Fortress.
Allows running OS shell commands, interactive agents (e.g. agy), Python snippets,
and fortress commands with non-blocking real-time streaming output or external window spawning.
"""

from __future__ import annotations
import asyncio
import os
import shutil
import subprocess
import sys
from typing import Optional

from textual.app import ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from rich.text import Text

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus, Event, EventType


class InteractiveShellPane(Vertical):
    """An interactive system and fortress shell pane with live streaming execution."""

    def __init__(self, state: FortressState, event_bus: EventBus) -> None:
        super().__init__(classes="pane-container shell-container")
        self.state = state
        self.event_bus = event_bus
        self.active_proc: Optional[asyncio.subprocess.Process] = None

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
            f"[cyan]Kullanılabilir: Sistem komutları (agy, python, dir, git), fortress komutları (banana, export, heal), 'open <komut>' veya 'stop'.[/cyan]\n"
        )
        log.write(banner)

    async def execute_command(self, cmd_str: str) -> None:
        """Executes a command safely without blocking the Textual event loop."""
        log = self.query_one("#shell-stream", RichLog)
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return

        log.write(f"\n[bold #FFE135]shell>[/bold #FFE135] [white]{cmd_str}[/white]")

        # 1. Process termination commands
        if cmd_str.lower() in ("stop", "kill", "quit", "exit", "^c", "c"):
            if self.active_proc and self.active_proc.returncode is None:
                pid = self.active_proc.pid
                try:
                    if os.name == "nt":
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                    else:
                        self.active_proc.kill()
                    log.write(f"[bold red]🛑 Process (PID: {pid}) sonlandırıldı.[/bold red]")
                except Exception as e:
                    log.write(f"[red]Process sonlandırılamadı: {e}[/red]")
                self.active_proc = None
                return

        # 2. If a process is already running, pipe input to its stdin
        if self.active_proc and self.active_proc.returncode is None:
            try:
                if self.active_proc.stdin and not self.active_proc.stdin.is_closing():
                    self.active_proc.stdin.write(cmd_str.encode("utf-8") + b"\n")
                    await self.active_proc.stdin.drain()
                    log.write(f"[dim yellow]→ [stdin]: {cmd_str}[/dim yellow]")
                    return
            except Exception as e:
                log.write(f"[dim red]Stdin iletilemedi: {e}[/dim red]")

        # 3. Built-in quick commands
        if cmd_str.lower() in ("clear", "cls"):
            log.clear()
            return

        if cmd_str.lower() in ("help", "?"):
            help_text = (
                "[bold cyan]Kullanılabilir Shell Komutları:[/bold cyan]\n"
                "• [yellow]Herhangi Bir Komut:[/yellow] agy, python, dir, ping, git, npm, curl, echo...\n"
                "• [yellow]Harici Konsol:[/yellow] 'open <komut>' veya 'start <komut>' ile yeni Windows konsolunda açabilirsiniz.\n"
                "• [yellow]Fortress Komutları:[/yellow] @01 pause, @01 resume, banana, heal 01, export, detach\n"
                "• [yellow]Durdurma:[/yellow] Çalışan bir komutu 'stop' veya 'kill' yazarak sonlandırabilirsiniz.\n"
                "• [yellow]clear / cls:[/yellow] Ekranı temizler."
            )
            log.write(help_text)
            return

        # 4. Fortress direct commands
        tokens = cmd_str.split()
        first = tokens[0].lower()
        if tokens[0].startswith("@") or first in ("banana", "heal", "export", "detach", "spawn", "layout", "preset"):
            await self.event_bus.publish(
                Event(
                    type=EventType.COMMAND,
                    source="shell_pane",
                    data={"command": cmd_str},
                )
            )
            log.write(f"[dim green]✔ Fortress Core'a iletildi: {cmd_str}[/dim green]")
            return

        # 5. Harici Pencerede Başlatma (start / open)
        if first in ("start", "open"):
            target_cmd = " ".join(tokens[1:]) or "cmd.exe"
            try:
                if os.name == "nt":
                    subprocess.Popen(f'start "{target_cmd}" cmd /k "{target_cmd}"', shell=True)
                else:
                    subprocess.Popen(f'x-terminal-emulator -e "{target_cmd}" || xterm -e "{target_cmd}"', shell=True)
                log.write(f"[bold green]✔ Harici terminal penceresinde başlatıldı:[/bold green] [yellow]{target_cmd}[/yellow]")
            except Exception as e:
                log.write(f"[bold red]Harici pencere açılamadı:[/bold red] {e}")
            return

        # 6. İnteraktif TUI Tespiti (Örn: agy, powershell, cmd, bash, vim)
        # agy gibi tam TUI tabanlı uygulamalar curses/lipgloss arabirimi gerektirdiğinden
        # -p (print) modu belirtilmemişse bağımsız Windows konsolunda başlatılır.
        is_interactive_tui = False
        if first == "agy":
            # agy -p veya --print veya help text modları haricinde interaktiftir
            if not any(flag in tokens for flag in ("-p", "--print", "--help", "-h", "version", "--version")):
                is_interactive_tui = True
        elif first in ("powershell", "cmd", "bash", "wsl", "vim", "nano", "htop"):
            is_interactive_tui = True
        elif first == "python" and len(tokens) == 1:
            is_interactive_tui = True

        if is_interactive_tui:
            try:
                if os.name == "nt":
                    subprocess.Popen(f'start "{cmd_str}" cmd /k "{cmd_str}"', shell=True)
                else:
                    subprocess.Popen(f'x-terminal-emulator -e "{cmd_str}" || xterm -e "{cmd_str}"', shell=True)
                log.write(f"[bold green]✔ İnteraktif CLI ({first}) bağımsız terminal penceresinde başlatıldı![/bold green]")
                log.write(f"[dim cyan]İpucu: Komut satırı çıktılarını doğrudan bu pencerede görmek için 'agy -p \"mesaj\"' formatını kullanabilirsiniz.[/dim cyan]")
            except Exception as e:
                log.write(f"[bold red]İnteraktif pencere başlatılamadı:[/bold red] {e}")
            return

        # 7. Asenkron Akışlı (Streaming) Komut Çalıştırma (Asla Textual'ı kilitlemez!)
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.active_proc = proc
            log.write(f"[dim cyan]▶ Çalışıyor (PID: {proc.pid}) — Durdurmak için 'stop' yazabilirsiniz.[/dim cyan]")
            asyncio.create_task(self._stream_proc(proc, cmd_str))
        except Exception as e:
            log.write(f"[bold red]Process başlatılamadı:[/bold red] {e}")

    async def _stream_proc(self, proc: asyncio.subprocess.Process, cmd_str: str) -> None:
        log = self.query_one("#shell-stream", RichLog)

        async def read_stream(stream, is_err: bool = False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    prefix = "[red][ERR][/red] " if is_err else ""
                    self.app.call_later(log.write, f"{prefix}{text}")

        try:
            await asyncio.gather(
                read_stream(proc.stdout, is_err=False),
                read_stream(proc.stderr, is_err=True),
            )
            code = await proc.wait()
            if code == 0:
                self.app.call_later(log.write, f"[dim green]✔ Tamamlandı: {cmd_str} (Exit code 0)[/dim green]")
            else:
                self.app.call_later(log.write, f"[dim red]Process sonlandı: exit code {code}[/dim red]")
        except asyncio.CancelledError:
            if proc.returncode is None:
                proc.kill()
        finally:
            if self.active_proc == proc:
                self.active_proc = None
