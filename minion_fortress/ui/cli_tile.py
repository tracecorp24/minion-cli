"""
Modular CLI Tile Pane for Minion Fortress Dynamic Tiling Workspace.
Each tile operates as an independent CLI instance (Minions, Shell, Error Monitor,
Sniper, or Plugin Hub) with its own dedicated command input, right-click context menu,
and hot-switchable CLI modes.
"""

from __future__ import annotations
import asyncio
import os
import subprocess
from typing import Optional, Callable, Any
from textual.app import ComposeResult
from textual.widgets import Static, Button, Input
from textual.containers import Vertical, Horizontal
from textual import events

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.panes.minion_pane import MinionPane
from minion_fortress.ui.panes.error_pane import ErrorHealthPane
from minion_fortress.ui.panes.sniper_pane import LogSniperPane
from minion_fortress.ui.panes.plugin_pane import PluginPane
from minion_fortress.ui.panes.shell_pane import InteractiveShellPane
from minion_fortress.ui.context_menu import TileContextMenu, CliSelectorModal


class CliTilePane(Vertical):
    """An independent CLI pane tile that can be split, detached, resized, or switched."""

    DEFAULT_CSS = """
    CliTilePane {
        border: heavy #FFE135;
        background: #181818;
        height: 1fr;
        width: 1fr;
        margin: 0;
        padding: 0;
    }
    CliTilePane:focus-within {
        border: heavy #00FF7F;
    }
    .tile-header-bar {
        height: 1;
        background: #202020;
        padding: 0 1;
        layout: horizontal;
    }
    .tile-title-text {
        width: 1fr;
        height: 1;
        color: #FFE135;
        text-style: bold;
        overflow-x: hidden;
        text-overflow: ellipsis;
    }
    .tile-actions-strip {
        width: auto;
        layout: horizontal;
    }
    .tile-hdr-btn {
        width: 4;
        min-width: 4;
        height: 1;
        padding: 0;
        margin: 0 0 0 1;
        background: #333333;
        color: #FFFFFF;
        border: none;
    }
    .tile-hdr-btn:hover {
        background: #FFE135;
        color: #000000;
        text-style: bold;
    }
    .tile-hdr-btn-danger:hover {
        background: #FF4444;
        color: #FFFFFF;
    }
    .tile-inner-container {
        height: 1fr;
        width: 100%;
        padding: 0;
        margin: 0;
    }
    .tile-input-container {
        height: 3;
        min-height: 3;
        max-height: 3;
        background: #141414;
        border-top: heavy #FFE135;
        padding: 0 1;
        layout: horizontal;
    }
    CliTilePane:focus-within .tile-input-container {
        border-top: heavy #00FF7F;
        background: #181818;
    }
    .tile-prompt-tag {
        width: auto;
        height: 1;
        color: #00FF7F;
        text-style: bold;
        content-align: center middle;
        padding-right: 1;
    }
    .tile-cli-input {
        width: 1fr;
        height: 1;
        background: #0A0A0A;
        border: none;
        padding: 0;
        color: #FFFFFF;
    }
    .tile-cli-input:focus {
        background: #000000;
        color: #FFE135;
    }
    CliTilePane .pane-container {
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 1fr !important;
        width: 100% !important;
    }
    CliTilePane .pane-title {
        display: none !important;
    }
    CliTilePane .minion-avatar-box {
        border: none !important;
        padding: 0 1 !important;
        margin: 0 !important;
        height: auto !important;
        max-height: 2 !important;
        background: #141414 !important;
        color: #FFE135 !important;
    }
    CliTilePane .action-bar {
        height: 1 !important;
        padding: 0 1 !important;
        margin: 0 !important;
        background: #181818 !important;
    }
    CliTilePane .action-bar Button {
        height: 1 !important;
        min-width: 5 !important;
        border: none !important;
        padding: 0 !important;
        margin-right: 1 !important;
    }
    CliTilePane .log-stream {
        height: 1fr !important;
        min-height: 2 !important;
    }
    CliTilePane #sniper-regex-input {
        height: 1 !important;
        border: none !important;
        padding: 0 1 !important;
    }
    CliTilePane #sniper-status-bar {
        height: 1 !important;
        padding: 0 1 !important;
    }
    CliTilePane #error-telemetry-badge {
        height: 1 !important;
        padding: 0 1 !important;
    }
    """

    def __init__(
        self,
        tile_id: str,
        cli_type: str = "minion-01",
        state: Optional[FortressState] = None,
        event_bus: Optional[EventBus] = None,
        plugin_manager: Optional[PluginManager] = None,
        on_action: Optional[Callable[[str, str, Any], None]] = None,
    ) -> None:
        super().__init__(id=tile_id)
        self.tile_id = tile_id
        self.cli_type = cli_type
        self.state = state or FortressState()
        self.event_bus = event_bus or EventBus()
        self.plugin_manager = plugin_manager
        self.on_action = on_action
        self._current_widget = None

    def compose(self) -> ComposeResult:
        # Header bar with title and quick action buttons
        with Horizontal(classes="tile-header-bar"):
            yield Static(self._format_title(), id=f"title-{self.tile_id}", classes="tile-title-text")
            with Horizontal(classes="tile-actions-strip"):
                yield Button("⬌", id=f"btn-vsplit-{self.tile_id}", classes="tile-hdr-btn", tooltip="Dikey Böl (Sağa Ekle)")
                yield Button("⬍", id=f"btn-hsplit-{self.tile_id}", classes="tile-hdr-btn", tooltip="Yatay Böl (Aşağı Ekle)")
                yield Button("🗗", id=f"btn-detach-{self.tile_id}", classes="tile-hdr-btn", tooltip="Birleşik Düzenden Ayır")
                yield Button("🔄", id=f"btn-switch-{self.tile_id}", classes="tile-hdr-btn", tooltip="CLI Türünü Değiştir")
                yield Button("✖", id=f"btn-close-{self.tile_id}", classes="tile-hdr-btn tile-hdr-btn-danger", tooltip="Pencereyi Kapat")

        # Inner Content Box
        with Vertical(id=f"content-{self.tile_id}", classes="tile-inner-container"):
            yield self._create_cli_widget()

        # Dedicated per-tile command prompt
        with Horizontal(classes="tile-input-container"):
            yield Static(f"[{self.cli_type}]>", id=f"prompt-lbl-{self.tile_id}", classes="tile-prompt-tag")
            yield Input(
                placeholder=self._get_input_placeholder(),
                id=f"input-{self.tile_id}",
                classes="tile-cli-input",
            )

    def _format_title(self) -> str:
        tag_map = {
            "shell": "💻 INTERACTIVE SHELL CLI",
            "error": "🚨 WATCHDOG ERROR & HEALTH",
            "sniper": "🎯 LIVE LOG SNIPER",
            "plugins": "🧩 PLUGIN & TOOL STORE",
        }
        if self.cli_type.startswith("minion-"):
            mid = self.cli_type.replace("minion-", "")
            m = self.state.minions.get(mid)
            m_name = m.name if m else f"worker-{mid}"
            m_st = m.status.value if m else "RUNNING"
            return f"🤖 MINION-{mid} [{m_name}] ({m_st}) │ Sağ Tık: Menü"
        return f"{tag_map.get(self.cli_type, self.cli_type.upper())} │ Sağ Tık: Menü"

    def _get_input_placeholder(self) -> str:
        if self.cli_type.startswith("minion-"):
            return "Komut: pause, resume, error, replay, model <name>, banana..."
        elif self.cli_type == "shell":
            return "Shell Komutu: dir, git, python, banana, heal, help..."
        elif self.cli_type == "error":
            return "Hata İşlemi: heal 01, heal 02, clear, banana..."
        elif self.cli_type == "sniper":
            return "Sniper Regex Filtresi: AST, [ERROR|429], worker..."
        elif self.cli_type == "plugins":
            return "Eklenti Komutu: toggle <name>, reload..."
        return "Komut girin..."

    def _create_cli_widget(self):
        if self.cli_type.startswith("minion-"):
            mid = self.cli_type.replace("minion-", "")
            w = MinionPane(self.state, self.event_bus, initial_minion_id=mid)
        elif self.cli_type == "shell":
            w = InteractiveShellPane(self.state, self.event_bus)
        elif self.cli_type == "error":
            w = ErrorHealthPane(self.state, self.event_bus)
        elif self.cli_type == "sniper":
            w = LogSniperPane(self.state, self.event_bus)
        elif self.cli_type == "plugins":
            w = PluginPane(self.state, self.event_bus, self.plugin_manager)
        else:
            w = InteractiveShellPane(self.state, self.event_bus)

        self._current_widget = w
        return w

    async def switch_cli(self, new_cli_type: str) -> None:
        """Dynamically switches this tile's running CLI type."""
        if new_cli_type == self.cli_type:
            return

        self.cli_type = new_cli_type
        # Update title
        title_widget = self.query_one(f"#title-{self.tile_id}", Static)
        title_widget.update(self._format_title())

        # Update prompt tag and placeholder
        prompt_lbl = self.query_one(f"#prompt-lbl-{self.tile_id}", Static)
        prompt_lbl.update(f"[{self.cli_type}]>")
        inp = self.query_one(f"#input-{self.tile_id}", Input)
        inp.placeholder = self._get_input_placeholder()

        # Replace inner widget
        content_box = self.query_one(f"#content-{self.tile_id}", Vertical)
        for child in list(content_box.children):
            await child.remove()

        new_widget = self._create_cli_widget()
        await content_box.mount(new_widget)
        self.call_after_refresh(self.focus_input)

    def focus_input(self) -> None:
        """Focuses the command input of this tile."""
        try:
            inp = self.query_one(f"#input-{self.tile_id}", Input)
            inp.focus()
        except Exception:
            pass

    def on_mount(self) -> None:
        self.call_after_refresh(self.focus_input)

    def on_click(self, event: events.Click) -> None:
        """Right-click opens the context menu modal; left-click focuses command input."""
        if event.button == 3:  # Right-click
            event.stop()
            self._open_context_menu()
        elif event.button == 1:
            try:
                clicked = self.screen.get_widget_at(event.screen_x, event.screen_y)[0]
                if not isinstance(clicked, Button):
                    self.focus_input()
            except Exception:
                self.focus_input()

    def on_key(self, event: events.Key) -> None:
        """Ensure printable keystrokes inside tile focus and reach the command input."""
        try:
            inp = self.query_one(f"#input-{self.tile_id}", Input)
            if self.app.focused != inp and event.is_printable:
                inp.focus()
        except Exception:
            pass

    def _open_context_menu(self) -> None:
        def _handle_menu_result(result: dict) -> None:
            if not result or result.get("action") == "cancel":
                return
            action = result.get("action")
            if action == "open_cli_selector":
                self._open_cli_selector()
            elif self.on_action:
                self.on_action(action, self.tile_id, result)

        self.app.push_screen(TileContextMenu(self.tile_id, self.cli_type), _handle_menu_result)

    def _open_cli_selector(self) -> None:
        def _handle_selection(selected_cli: Optional[str]) -> None:
            if selected_cli:
                asyncio.create_task(self.switch_cli(selected_cli))

        self.app.push_screen(CliSelectorModal(self.tile_id, self.cli_type), _handle_selection)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == f"btn-vsplit-{self.tile_id}":
            if self.on_action:
                self.on_action("split_v", self.tile_id, {})
        elif btn_id == f"btn-hsplit-{self.tile_id}":
            if self.on_action:
                self.on_action("split_h", self.tile_id, {})
        elif btn_id == f"btn-detach-{self.tile_id}":
            if self.on_action:
                self.on_action("detach", self.tile_id, {"cli_type": self.cli_type})
        elif btn_id == f"btn-switch-{self.tile_id}":
            self._open_cli_selector()
        elif btn_id == f"btn-close-{self.tile_id}":
            if self.on_action:
                self.on_action("close", self.tile_id, {})

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles commands submitted specifically to this tile's CLI."""
        if event.input.id != f"input-{self.tile_id}":
            return

        cmd = event.value.strip()
        event.input.value = ""
        if not cmd:
            return

        await self._dispatch_tile_command(cmd)

    async def _dispatch_tile_command(self, cmd: str) -> None:
        parts = cmd.split()
        first = parts[0].lower()

        # If it's a shell pane, execute directly via InteractiveShellPane
        if self.cli_type == "shell":
            if isinstance(self._current_widget, InteractiveShellPane):
                await self._current_widget.execute_command(cmd)
            return

        # If it's a minion pane
        if self.cli_type.startswith("minion-"):
            mid = self.cli_type.replace("minion-", "")
            minion_cmds = ("pause", "resume", "error", "crash", "replay", "live", "model", "task", "status")
            fortress_cmds = ("banana", "export", "detach", "heal", "help", "spawn", "layout", "preset")

            # Check if it's a known minion or fortress command
            if first.startswith("@") or first in minion_cmds or first in fortress_cmds:
                full_cmd = f"@{mid} {cmd}" if not first.startswith("@") and first not in fortress_cmds else cmd
                await self.event_bus.publish(
                    Event(
                        type=EventType.COMMAND,
                        source=f"tile_{self.tile_id}",
                        data={"command": full_cmd},
                    )
                )
                return

            # Otherwise, the operator typed a system command or tool (e.g. agy, python, dir, git)
            # If it's agy or an interactive shell app, launch safely in external console or switch to shell:
            if first == "agy" or first in ("start", "open", "powershell", "cmd", "bash"):
                target_cmd = " ".join(parts[1:]) if first in ("start", "open") else cmd
                if not target_cmd:
                    target_cmd = "cmd.exe"
                try:
                    if os.name == "nt":
                        subprocess.Popen(f'start "{target_cmd}" cmd /k "{target_cmd}"', shell=True)
                    else:
                        subprocess.Popen(f'x-terminal-emulator -e "{target_cmd}" || xterm -e "{target_cmd}"', shell=True)
                    self.app.notify(f"🚀 Harici terminalde başlatıldı: {target_cmd}", title="CLI BAŞLATILDI")
                except Exception as e:
                    self.app.notify(f"Terminal başlatılamadı: {e}", severity="error")
                return

            # For general shell commands entered in a minion pane, auto-switch to shell and execute!
            await self.switch_cli("shell")
            if isinstance(self._current_widget, InteractiveShellPane):
                await self._current_widget.execute_command(cmd)
            return

        # If error pane
        if self.cli_type == "error":
            if first in ("heal", "repair"):
                target = parts[1] if len(parts) > 1 else "01"
                await self.event_bus.publish(
                    Event(type=EventType.COMMAND, source=self.tile_id, data={"command": f"heal {target}"})
                )
            elif first == "clear":
                try:
                    self._current_widget.query_one("#error-log-stream").clear()
                except Exception:
                    pass
            else:
                await self.event_bus.publish(
                    Event(type=EventType.COMMAND, source=self.tile_id, data={"command": cmd})
                )
            return

        # If sniper pane
        if self.cli_type == "sniper":
            try:
                sniper_input = self._current_widget.query_one("#sniper-regex-input", Input)
                sniper_input.value = cmd
            except Exception:
                pass
            return

        # If plugins pane
        if self.cli_type == "plugins":
            if first in ("toggle", "rescan"):
                await self.event_bus.publish(
                    Event(type=EventType.COMMAND, source=self.tile_id, data={"command": f"plugin {cmd}"})
                )
            return

        # Default fallback
        await self.event_bus.publish(
            Event(type=EventType.COMMAND, source=self.tile_id, data={"command": cmd})
        )
