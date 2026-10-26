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
from typing import Optional, Callable, List

from textual.app import ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from rich.markup import escape

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus, Event, EventType


class InteractiveShellPane(Vertical):
    """An interactive system, agent (agy) and fortress shell pane with live streaming execution."""

    def __init__(
        self,
        state: FortressState,
        event_bus: EventBus,
        initial_agy_mode: bool = False,
        on_mode_change: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(classes="pane-container shell-container")
        self.state = state
        self.event_bus = event_bus
        self.agy_mode = initial_agy_mode
        self.agy_flags: List[str] = ["--dangerously-skip-permissions"]
        self.on_mode_change = on_mode_change
        self.active_proc: Optional[asyncio.subprocess.Process] = None

    def compose(self) -> ComposeResult:
        title = "🤖 ANTIGRAVITY AGENT CLI" if self.agy_mode else "💻 INTERACTIVE SHELL CLI"
        yield Static(f"{title} (System & Fortress Console)", classes="pane-title shell-title")
        yield RichLog(id="shell-stream", classes="log-stream", highlight=True, markup=True)

    def on_mount(self) -> None:
        log = self.query_one("#shell-stream", RichLog)
        cwd = os.getcwd()
        py_ver = sys.version.split()[0]
        if self.agy_mode:
            banner = (
                f"[bold #00FF7F]🤖 Antigravity AI Agent CLI Aktif[/bold #00FF7F]\n"
                f"[dim]Working directory: {escape(cwd)} │ Parametreler: {' '.join(self.agy_flags)}[/dim]\n"
                f"[cyan]• Mesaj, prompt veya kodlama görevinizi aşağıya yazıp Enter'a basın.[/cyan]\n"
                f"[dim]• Durdurmak için 'stop', standart kabuğa dönmek için 'exit' yazabilirsiniz.\n"
                f"• Harici tam TUI penceresinde açmak için 'open agy' yazabilirsiniz.[/dim]\n"
            )
        else:
            banner = (
                f"[bold #00FF7F]Minion-Fortress Shell v3.0[/bold #00FF7F] (Python {py_ver})\n"
                f"[dim]Working directory: {escape(cwd)}[/dim]\n"
                f"[cyan]Kullanılabilir: Sistem komutları (agy, python, dir, git), fortress komutları (banana, export, heal), 'open <komut>' veya 'stop'.[/cyan]\n"
            )
        log.write(banner)

    async def execute_command(self, cmd_str: str) -> None:
        """Executes a command safely without blocking the Textual event loop."""
        log = self.query_one("#shell-stream", RichLog)
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return

        cmd_lower = cmd_str.lower()

        # -------------------------------------------------------------
        # A. AGY AGENT MODE ACTIVE
        # -------------------------------------------------------------
        if self.agy_mode:
            # 1. AGY Stop / Exit commands
            if cmd_lower in ("stop", "kill", "durdur"):
                if self.active_proc and self.active_proc.returncode is None:
                    pid = self.active_proc.pid
                    try:
                        if os.name == "nt":
                            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                        else:
                            self.active_proc.kill()
                        log.write(f"[bold red]🛑 Aktif Antigravity işlemi (PID: {pid}) durduruldu.[/bold red]")
                    except Exception as e:
                        log.write(f"[red]İşlem durdurulamadı: {escape(str(e))}[/red]")
                    self.active_proc = None
                else:
                    log.write("[dim yellow]Şu anda çalışan bir arka plan işlemi yok.[/dim yellow]")
                return

            if cmd_lower in ("exit", "quit", "q", "/exit", "/quit", "exit()"):
                if self.active_proc and self.active_proc.returncode is None:
                    try:
                        if os.name == "nt":
                            subprocess.run(f"taskkill /F /T /PID {self.active_proc.pid}", shell=True, capture_output=True)
                        else:
                            self.active_proc.kill()
                    except Exception:
                        pass
                    self.active_proc = None

                self.agy_mode = False
                if self.on_mode_change:
                    self.on_mode_change("shell", "Shell Komutu: dir, git, python, banana, heal, help...")
                log.write("[dim yellow]Antigravity oturumu sonlandırıldı. Standart shell moduna dönüldü.[/dim yellow]")
                return

            if cmd_lower in ("clear", "cls"):
                log.clear()
                return

            if cmd_lower in ("help", "?"):
                help_text = (
                    "[bold cyan]Antigravity Agent CLI Komutları:[/bold cyan]\n"
                    "• [yellow]Mesaj / Prompt:[/yellow] Doğrudan prompt veya görevi yazın (örn: 'bu repo ne işe yarar?').\n"
                    "• [yellow]stop / durdur:[/yellow] Çalışmakta olan model yanıtını anında durdurur.\n"
                    "• [yellow]exit / quit:[/yellow] Agent oturumundan çıkıp standart kabuğa döner.\n"
                    "• [yellow]open agy:[/yellow] Ayrı bir Windows CMD konsolunda tam BubbleTea TUI olarak açar.\n"
                    "• [yellow]clear / cls:[/yellow] Ekranı temizler."
                )
                log.write(help_text)
                return

            if cmd_lower.startswith("open") or cmd_lower.startswith("start"):
                tokens = cmd_str.split()
                target_cmd = " ".join(tokens[1:]) or "agy --dangerously-skip-permissions"
                try:
                    if os.name == "nt":
                        subprocess.Popen(f'start "{target_cmd}" cmd /k "{target_cmd}"', shell=True)
                    else:
                        subprocess.Popen(f'x-terminal-emulator -e "{target_cmd}" || xterm -e "{target_cmd}"', shell=True)
                    log.write(f"[bold green]✔ Harici terminal penceresinde başlatıldı:[/bold green] [yellow]{escape(target_cmd)}[/yellow]")
                except Exception as e:
                    log.write(f"[bold red]Harici pencere açılamadı:[/bold red] {escape(str(e))}")
                return

            # Check if previous turn is still running
            if self.active_proc and self.active_proc.returncode is None:
                log.write("[dim yellow]⚠ Önceki Antigravity görevi hala çalışıyor. Durdurmak için 'stop' yazın.[/dim yellow]")
                return

            # Strip leading 'agy' if user typed 'agy <prompt>'
            prompt_text = cmd_str
            if prompt_text.lower().startswith("agy "):
                prompt_text = prompt_text[4:].strip()

            log.write(f"\n[bold #00FF7F]agy>[/bold #00FF7F] [white]{escape(prompt_text)}[/white]")
            log.write("[dim cyan]⏳ Antigravity yanıtlıyor...[/dim cyan]")

            agy_bin = shutil.which("agy") or "agy"
            cmd_args = [agy_bin] + self.agy_flags + ["-c", "-p", prompt_text]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self.active_proc = proc
                asyncio.create_task(self._stream_proc(proc, f"agy: {prompt_text[:25]}"))
            except Exception as e:
                log.write(f"[bold red]Antigravity başlatılamadı:[/bold red] {escape(str(e))}")
            return

        # -------------------------------------------------------------
        # B. STANDARD SHELL MODE
        # -------------------------------------------------------------
        log.write(f"\n[bold #FFE135]shell>[/bold #FFE135] [white]{escape(cmd_str)}[/white]")

        # 1. Process termination commands
        if cmd_lower in ("stop", "kill", "quit", "exit", "^c", "c"):
            if self.active_proc and self.active_proc.returncode is None:
                pid = self.active_proc.pid
                try:
                    if os.name == "nt":
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                    else:
                        self.active_proc.kill()
                    log.write(f"[bold red]🛑 Process (PID: {pid}) sonlandırıldı.[/bold red]")
                except Exception as e:
                    log.write(f"[red]Process sonlandırılamadı: {escape(str(e))}[/red]")
                self.active_proc = None
                return

        # 2. If a non-agent process is already running, pipe input to its stdin
        if self.active_proc and self.active_proc.returncode is None:
            try:
                if self.active_proc.stdin and not self.active_proc.stdin.is_closing():
                    self.active_proc.stdin.write(cmd_str.encode("utf-8") + b"\n")
                    await self.active_proc.stdin.drain()
                    log.write(f"[dim yellow]→ [stdin]: {escape(cmd_str)}[/dim yellow]")
                    return
            except Exception as e:
                log.write(f"[dim red]Stdin iletilemedi: {escape(str(e))}[/dim red]")

        # 3. Built-in quick commands
        if cmd_lower in ("clear", "cls"):
            log.clear()
            return

        if cmd_lower in ("help", "?"):
            help_text = (
                "[bold cyan]Kullanılabilir Shell Komutları:[/bold cyan]\n"
                "• [yellow]Antigravity AI:[/yellow] 'agy' veya 'agy --dangerously-skip-permissions' yazarak canlı AI agent başlatın.\n"
                "• [yellow]Herhangi Bir Sistem Komutu:[/yellow] python, dir, ping, git, npm, curl, echo...\n"
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
            log.write(f"[dim green]✔ Fortress Core'a iletildi: {escape(cmd_str)}[/dim green]")
            return

        # 5. Harici Pencerede Başlatma (yalnızca kullanıcı açıkça 'start' veya 'open' yazarsa)
        if first in ("start", "open"):
            target_cmd = " ".join(tokens[1:]) or "cmd.exe"
            try:
                if os.name == "nt":
                    subprocess.Popen(f'start "{target_cmd}" cmd /k "{target_cmd}"', shell=True)
                else:
                    subprocess.Popen(f'x-terminal-emulator -e "{target_cmd}" || xterm -e "{target_cmd}"', shell=True)
                log.write(f"[bold green]✔ Harici terminal penceresinde başlatıldı:[/bold green] [yellow]{escape(target_cmd)}[/yellow]")
            except Exception as e:
                log.write(f"[bold red]Harici pencere açılamadı:[/bold red] {escape(str(e))}")
            return

        # 6. Agı Komutu Tespiti: agy / agy.exe
        if first in ("agy", "agy.exe"):
            has_print = any(t in tokens for t in ("-p", "--print", "--prompt"))
            is_subcmd = any(t in tokens for t in ("--version", "-v", "--help", "-h", "update", "models", "agents", "help"))
            if not has_print and not is_subcmd:
                # Kullanıcı interaktif agy çalıştırmak istiyor!
                # Doğrudan pipe ile BubbleTea başlatmak Windows'ta kilitlenmeye yol açtığından,
                # bu bölmede kesintisiz streaming sohbet/kodlama oturumunu aktif ediyoruz.
                flags = [t for t in tokens[1:] if not t.startswith("-p")]
                if "--dangerously-skip-permissions" not in flags:
                    flags.append("--dangerously-skip-permissions")
                self.agy_flags = flags
                self.agy_mode = True
                if self.on_mode_change:
                    self.on_mode_change("agy", "Antigravity'ye prompt yazın (Durdurmak için 'stop')...")

                banner = (
                    f"\n[bold #00FF7F]🤖 ANTIGRAVITY AGENT CLI AKTİF[/bold #00FF7F] [dim](Canlı Akış Modu)[/dim]\n"
                    f"[dim]• Parametreler: {escape(' '.join(self.agy_flags))}[/dim]\n"
                    f"[cyan]• Mesaj veya görevinizi aşağıya yazıp Enter'a basın.[/cyan]\n"
                    f"[dim]• Çıkmak için: 'exit' veya 'stop' yazın.\n"
                    f"• Ayrı bir Windows konsolunda TUI olarak açmak isterseniz: 'open agy'[/dim]\n"
                )
                log.write(banner)
                return

        # 7. Doğrudan bu Bölmede (In-Pane) Canlı Akışlı Asenkron Çalıştırma
        # python, powershell, git, dir ve tüm sistem araçları bu bölmede akar!
        run_cmd = cmd_str
        if first == "python" and len(tokens) == 1:
            run_cmd = "python -i -q"

        try:
            proc = await asyncio.create_subprocess_shell(
                run_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.active_proc = proc
            log.write(f"[dim cyan]▶ Çalışıyor (PID: {proc.pid}) — Durdurmak için 'stop' yazabilirsiniz.[/dim cyan]")
            asyncio.create_task(self._stream_proc(proc, cmd_str))
        except Exception as e:
            log.write(f"[bold red]Process başlatılamadı:[/bold red] {escape(str(e))}")

    async def _stream_proc(self, proc: asyncio.subprocess.Process, cmd_str: str) -> None:
        log = self.query_one("#shell-stream", RichLog)

        async def read_stream(stream, is_err: bool = False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                # Çoklu karakter kodlaması desteği (UTF-8, Türkçe Windows CP1254/CP857, Latin1)
                text = ""
                for enc in ("utf-8", "cp1254", "cp857", "latin1"):
                    try:
                        text = line.decode(enc).rstrip("\r\n")
                        break
                    except Exception:
                        continue
                if not text:
                    text = line.decode("utf-8", errors="replace").rstrip("\r\n")

                if text:
                    prefix = "[red][ERR][/red] " if is_err else ""
                    self.app.call_later(log.write, f"{prefix}{escape(text)}")

        try:
            await asyncio.gather(
                read_stream(proc.stdout, is_err=False),
                read_stream(proc.stderr, is_err=True),
            )
            code = await proc.wait()
            if code == 0:
                self.app.call_later(log.write, f"[dim green]✔ Tamamlandı ({escape(cmd_str)})[/dim green]")
            else:
                self.app.call_later(log.write, f"[dim red]Process sonlandı: exit code {code}[/dim red]")
        except asyncio.CancelledError:
            if proc.returncode is None:
                proc.kill()
        finally:
            if self.active_proc == proc:
                self.active_proc = None

