"""
Main Textual Application for Minion Fortress v3.0 (KOVAN-X).
Integrates Cluster Telemetry, Minion Roster, Dynamic 2x2 Tiling Canvas,
Watchdog Health Monitor, Log Sniper, Plugin Hub, Time Travel, Session Export,
Banana Mode, Interactive REPL, and Detached Window Auto-Spawner.
"""

from __future__ import annotations
import asyncio
import os
import psutil
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, DataTable
from textual.suggester import SuggestFromList

REPL_SUGGESTIONS = [
    "@01 pause",
    "@01 resume",
    "@01 replay",
    "@02 pause",
    "@02 resume",
    "@03 error",
    "@03 pause",
    "@04 resume",
    "@05 pause",
    "@model switch qwen-2.5-coder",
    "@model switch deepseek-r1",
    "@model switch glm-4-flash",
    "banana",
    "export",
    "detach",
    "heal 01",
    "heal 02",
    "heal 03",
    "spawn worker",
    "filter [ERROR|429]",
    "filter AST",
    "plugin toggle Docling-v2",
    "plugin toggle pgvector-sync",
    "plugin toggle Telegram-Bot",
    "plugin toggle OpenRouter-API",
    "help",
]

from minion_fortress.core.state import FortressState, MinionStatus
from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.theme import FORTRESS_CSS, BANANA_YELLOW, ERROR_RED, HEAL_GREEN
from minion_fortress.ui.panes.error_pane import ErrorHealthPane
from minion_fortress.ui.panes.sniper_pane import LogSniperPane
from minion_fortress.ui.panes.minion_pane import MinionPane
from minion_fortress.ui.panes.plugin_pane import PluginPane
from minion_fortress.ui.workspace import DynamicWorkspace
from minion_fortress.ui.cli_tile import CliTilePane


class MinionFortressApp(App):
    """Minion Fortress v3.0 Textual Application."""

    CSS = FORTRESS_CSS

    BINDINGS = [
        Binding("f2", "cycle_layout", "📐 Layout Değiştir", priority=True),
        Binding("f3", "split_vertical", "⬌ Dikey Böl", priority=True),
        Binding("f7", "split_horizontal", "⬍ Yatay Böl", priority=True),
        Binding("f12", "toggle_banana", "🍌 Banana Mode", priority=True),
        Binding("f8", "export_session", "📤 Export Session", priority=True),
        Binding("f4", "spawn_detached", "🪟 Detach Window", priority=True),
        Binding("f5", "rescan_plugins", "🔄 Rescan Plugins", priority=True),
        Binding("ctrl+q", "quit", "Quit Fortress", priority=True),
    ]

    def __init__(
        self,
        state: Optional[FortressState] = None,
        event_bus: Optional[EventBus] = None,
        daemon: Optional[MinionDaemon] = None,
        plugin_manager: Optional[PluginManager] = None,
        auto_spawn_detached: bool = True,
    ) -> None:
        super().__init__()
        self.state = state or FortressState()
        self.event_bus = event_bus or EventBus()
        self.plugin_manager = plugin_manager or PluginManager()
        self.plugin_manager.set_event_bus(self.event_bus)
        self.state.plugins = self.plugin_manager.get_all()
        self.daemon = daemon or MinionDaemon(self.state, self.event_bus, self.plugin_manager)
        self.auto_spawn_detached = auto_spawn_detached
        self.process = psutil.Process(os.getpid())
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        # Top Global Telemetry Banner
        yield Static(self._build_top_banner(), id="top-fortress-banner")

        # Main Workspace: Left Sidebar + Right Dynamic Tiling Workspace
        with Horizontal(id="app-grid"):
            # Left Sidebar: Cluster Telemetry & Minion Roster
            with Vertical(id="left-sidebar"):
                yield Static("📊 CLUSTER TELEMETRY", classes="section-header")
                yield Static(self._render_telemetry_box(), id="cluster-telemetry-box", classes="telemetry-card")
                yield Static("🤖 MINION ROSTER (Click to Focus)", classes="section-header")
                yield DataTable(id="minion-roster-table")

            # Right Workspace: Modular Dynamic Tiling Canvas with Presets and Drag Resizing
            yield DynamicWorkspace(self.state, self.event_bus, self.plugin_manager, initial_preset="grid_2x2")

        # Bottom Interactive REPL with Tab-Completion
        with Horizontal(id="repl-container"):
            yield Input(
                placeholder="minion> Type command (e.g. @01 pause, @03 error, banana, detach, export, help)...",
                id="repl-input",
                suggester=SuggestFromList(REPL_SUGGESTIONS, case_sensitive=False),
            )

        yield Footer()

    async def on_mount(self) -> None:
        # Start core daemon and event bus
        await self.event_bus.start()
        await self.daemon.start()

        # Listen for remote commands coming from detached window nodes over socket
        self.event_bus.subscribe(EventType.COMMAND, self._on_remote_command)

        # Set up Minion Roster Table
        table = self.query_one("#minion-roster-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("ID", "NAME", "STATUS", "CPU", "MODEL")
        self._populate_roster_table()

        # Periodic UI refresh loop (Zero-lag batching)
        self.set_interval(1.0, self._periodic_ui_refresh)

        # Automatically spawn second window (Detached Monitor Node) if enabled
        if self.auto_spawn_detached:
            self.call_after_refresh(self.action_spawn_detached)

    def _on_remote_command(self, event: Event) -> None:
        cmd = event.data.get("command", "")
        if cmd:
            asyncio.create_task(self._execute_repl_command(cmd))

    def _build_top_banner(self) -> str:
        cpu = psutil.cpu_percent(interval=None)
        ram_gb = psutil.virtual_memory().used / (1024 * 1024 * 1024)
        status_text = "🍌 STATUS: BANANA! 🟡" if self.state.banana_mode else "STATUS: NORMAL 🟢"
        active_count = self.state.get_active_minion_count()
        total_count = self.state.get_total_minion_count()
        pid = os.getpid()

        return (
            f" 🍌 MINION FORTRESS v3.0 │ {status_text} │ Active: {active_count}/{total_count} │ "
            f"CPU: {cpu}% │ RAM: {ram_gb:.1f}GB │ VRAM: 18.4GB │ [PID: {pid}]"
        )

    def _render_telemetry_box(self) -> str:
        rate = (self.state.completed_tasks / max(1, self.state.total_tasks)) * 100
        cost = self.state.token_cost
        uptime = int(time.time() - self.state.start_time)
        return (
            f"• Tasks: {self.state.completed_tasks}/{self.state.total_tasks} ({rate:.1f}%)\n"
            f"• Token Cost: ${cost:.4f}\n"
            f"• Uptime: {uptime}s │ Errors Caught: {len(self.state.error_logs)}\n"
            f"• Watchdog Shield: ARMED (5s auto-heal)"
        )

    def _populate_roster_table(self) -> None:
        try:
            table = self.query_one("#minion-roster-table", DataTable)
            table.clear()
            for mid, m in self.state.minions.items():
                st_color = {
                    MinionStatus.RUNNING: "green",
                    MinionStatus.BUSY: "cyan",
                    MinionStatus.IDLE: "dim",
                    MinionStatus.ERROR: "bold red",
                    MinionStatus.PAUSED: "yellow",
                    MinionStatus.HEALING: "bold magenta",
                }.get(m.status, "white")

                table.add_row(
                    f"[{st_color}]{m.id}[/{st_color}]",
                    f"[{st_color}]{m.name}[/{st_color}]",
                    f"[{st_color}]{m.status.value}[/{st_color}]",
                    f"{m.cpu}%",
                    m.model,
                    key=m.id,
                )
        except Exception:
            pass

    def _periodic_ui_refresh(self) -> None:
        """Lightweight UI sync every second."""
        try:
            banner = self.query_one("#top-fortress-banner", Static)
            banner.update(self._build_top_banner())

            tbox = self.query_one("#cluster-telemetry-box", Static)
            tbox.update(self._render_telemetry_box())

            self._populate_roster_table()
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Selecting a minion row in the table focuses it in the Minion Pane."""
        if event.row_key and event.row_key.value:
            selected_id = str(event.row_key.value)
            minion_panes = list(self.query(MinionPane))
            if minion_panes:
                minion_panes[0].set_minion(selected_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Navigating rows automatically previews that minion in Minion Pane."""
        if event.row_key and event.row_key.value:
            selected_id = str(event.row_key.value)
            minion_panes = list(self.query(MinionPane))
            if minion_panes and minion_panes[0].selected_minion_id != selected_id and not minion_panes[0].is_replay_mode:
                minion_panes[0].set_minion(selected_id)

    # -------------------------------------------------------------------------
    # Hotkey Actions
    # -------------------------------------------------------------------------
    def action_spawn_detached(self, cli_type: str = "all") -> None:
        """F4: Spawns the second window (Detached Monitor Node) automatically in a new OS console window."""
        root_path = Path(__file__).resolve().parent.parent.parent
        script_path = root_path / "detached_monitor.py"
        py_exec = sys.executable

        try:
            target_flag = f"--target {cli_type}" if cli_type != "all" else ""
            if os.name == "nt":
                cmd = f'start "MINION-FORTRESS: Detached Node [{cli_type.upper()}]" "{py_exec}" "{script_path}" {target_flag}'
                subprocess.Popen(cmd, shell=True)
            else:
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                    if shutil.which(term):
                        subprocess.Popen([term, "-e", f"{py_exec} {script_path} {target_flag}"])
                        break
                else:
                    args = [py_exec, str(script_path)]
                    if target_flag:
                        args.extend(["--target", cli_type])
                    subprocess.Popen(args)
            self.notify(f"🪟 Detached Node [{cli_type.upper()}] launched!", title="DETACHED NODE", severity="information")
        except Exception as e:
            self.notify(f"Could not spawn detached window: {e}", severity="warning")

    def action_cycle_layout(self) -> None:
        """F2: Cycles through layout presets."""
        presets = ["grid_2x2", "main_stack", "split_v", "split_h", "three_cols", "single"]
        ws = self.query_one(DynamicWorkspace)
        curr = ws.current_preset
        next_idx = (presets.index(curr) + 1) % len(presets) if curr in presets else 0
        self.run_worker(ws.apply_preset(presets[next_idx]))

    def action_split_vertical(self) -> None:
        """F3: Splits active tile vertically."""
        ws = self.query_one(DynamicWorkspace)
        if ws._active_tiles:
            target_id = list(ws._active_tiles.keys())[0]
            self.run_worker(ws.split_tile(target_id, direction="horizontal"))

    def action_split_horizontal(self) -> None:
        """F7: Splits active tile horizontally."""
        ws = self.query_one(DynamicWorkspace)
        if ws._active_tiles:
            target_id = list(ws._active_tiles.keys())[0]
            self.run_worker(ws.split_tile(target_id, direction="vertical"))

    def action_toggle_banana(self) -> None:
        """F12: Emergency Panic Banana Mode toggle."""
        is_banana = self.daemon.toggle_banana_mode()
        banner = self.query_one("#top-fortress-banner", Static)
        banner.update(self._build_top_banner())
        if is_banana:
            self.notify("🍌 BANANA MODE ACTIVATED! Cluster frozen in safe lockdown.", title="EMERGENCY ALERT", severity="warning")
        else:
            self.notify("🍌 BANANA MODE DISENGAGED. Normal operations resumed.", title="STATUS NORMAL", severity="information")

    def action_export_session(self) -> None:
        """F8: Export Session Snapshot to Markdown and JSON (Feature 9)."""
        reports_dir = Path("reports")
        md_file, json_file = self.state.export_snapshot(reports_dir)
        self.state.add_global_log("INFO", "fortress", f"Session snapshot exported: {md_file.name}")
        self.notify(f"Snapshot exported!\n📄 {md_file.name}\n📊 {json_file.name}", title="EXPORT COMPLETE", severity="information")

    def action_rescan_plugins(self) -> None:
        """F5: Rescan and reload plugins."""
        plugin_pane = self.query_one(PluginPane)
        self.plugin_manager.load_all()
        plugin_pane.refresh_plugins_list()
        self.notify("Plugins reloaded from disk.", title="PLUGIN HUB", severity="information")

    # -------------------------------------------------------------------------
    # Feature 10: Interactive Minion REPL Interpreter
    # -------------------------------------------------------------------------
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "repl-input":
            return

        cmd_raw = event.value.strip()
        event.input.value = ""
        if not cmd_raw:
            return

        await self._execute_repl_command(cmd_raw)

    async def _execute_repl_command(self, cmd: str) -> None:
        parts = cmd.split()
        root = parts[0].lower()

        # Target syntax support: @01 pause, @minion-01 resume, @model switch qwen
        if root.startswith("@"):
            target = root[1:]
            action = parts[1].lower() if len(parts) > 1 else "status"

            if target.startswith("minion-"):
                target_id = target.replace("minion-", "")
            else:
                target_id = target

            minion_panes = list(self.query(MinionPane))
            minion_pane = minion_panes[0] if minion_panes else None

            if target == "model" and action == "switch":
                model_name = parts[2] if len(parts) > 2 else "qwen-2.5-coder"
                if minion_pane:
                    self.daemon.switch_model(minion_pane.selected_minion_id, model_name)
                    self.notify(f"Switched model of Minion-{minion_pane.selected_minion_id} to {model_name}")
                return

            if target_id not in self.state.minions:
                self.notify(f"Minion-{target_id} not found in cluster roster.", severity="error")
                return

            if action == "pause":
                self.daemon.pause_minion(target_id)
                self.notify(f"Minion-{target_id} paused.")
            elif action == "resume":
                self.daemon.resume_minion(target_id)
                self.notify(f"Minion-{target_id} resumed.")
            elif action in ("error", "crash"):
                self.daemon.trigger_test_error(target_id)
                self.notify(f"Triggered simulated fault on Minion-{target_id} (Watchdog will auto-heal!)", severity="warning")
            elif action == "replay":
                if minion_pane:
                    minion_pane.set_minion(target_id)
                    minion_pane.is_replay_mode = True
                    minion_pane.replay_offset = 25
                    minion_pane.refresh_minion_display()
                self.notify(f"Time travel engaged for Minion-{target_id}")
            else:
                if minion_pane:
                    minion_pane.set_minion(target_id)
            return

        # Direct commands
        if root in ("banana", "panic"):
            self.action_toggle_banana()
        elif root in ("export", "snapshot"):
            self.action_export_session()
        elif root in ("layout", "preset"):
            preset = parts[1] if len(parts) > 1 else "grid_2x2"
            ws = self.query_one(DynamicWorkspace)
            self.run_worker(ws.apply_preset(preset))
        elif root == "split":
            direction = parts[1] if len(parts) > 1 else "v"
            if direction in ("v", "col", "vertical"):
                self.action_split_vertical()
            else:
                self.action_split_horizontal()
        elif root in ("detach", "window", "monitor"):
            self.action_spawn_detached()
        elif root in ("heal", "repair"):
            raw_target = parts[1] if len(parts) > 1 else "01"
            target_id = raw_target.replace("minion-", "").strip()
            if target_id not in self.state.minions:
                self.notify(f"Cannot heal: Minion-{target_id} not found.", severity="error")
                return
            await self.daemon._heal_minion(target_id, reason="Manual operator command")
            self.notify(f"Manual auto-heal initiated for minion-{target_id}")
        elif root == "spawn":
            name = parts[1] if len(parts) > 1 else f"worker-{len(self.state.minions)+1}"
            model = parts[2] if len(parts) > 2 else "qwen-2.5-coder"
            new_id = self.daemon.spawn_minion(name, model)
            self._populate_roster_table()
            self.notify(f"Spawned new minion-{new_id} ({name})", severity="information")
        elif root == "filter":
            regex_val = " ".join(parts[1:])
            sniper_input = self.query_one("#sniper-regex-input", Input)
            sniper_input.value = regex_val
            self.notify(f"Log Sniper filter set: {regex_val}")
        elif root in ("plugin", "tool"):
            if len(parts) >= 3 and parts[1] == "toggle":
                pname = parts[2]
                new_st = self.plugin_manager.toggle_plugin(pname)
                self.query_one(PluginPane).refresh_plugins_list()
                st_str = "ACTIVE" if new_st else "PAUSED"
                self.notify(f"Plugin [{pname}] is now {st_str}")
        elif root in ("help", "?"):
            help_text = (
                "Commands:\n"
                "• @<id> pause|resume|error|replay  (Control individual minion)\n"
                "• @model switch <name>             (Switch active model)\n"
                "• banana                           (Toggle Banana Mode - F12)\n"
                "• detach                           (Open Detached Monitor Window - F4)\n"
                "• export                           (Save session snapshot - F8)\n"
                "• heal <id>                        (Trigger watchdog healing)\n"
                "• spawn <name> [model]             (Spawn new worker)\n"
                "• filter <regex>                   (Set log sniper filter)\n"
                "• plugin toggle <name>             (Toggle plugin active/pause)"
            )
            self.notify(help_text, title="FORTRESS REPL HELP", timeout=8)
        else:
            self.notify(f"Unknown command: '{cmd}'. Type 'help' for command list.", severity="error")

    async def action_quit(self) -> None:
        await self.daemon.stop()
        await self.event_bus.stop()
        self.exit()
