"""
Dynamic Tiling Workspace for Minion Fortress v3.0.
Supports recursive horizontal/vertical splitting, draggable divider resizing,
per-tile CLI selection, detaching to independent OS windows, and layout presets.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from rich.text import Text

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.cli_tile import CliTilePane
from minion_fortress.ui.drag_splitter import DragSplitter


class DynamicWorkspace(Vertical):
    """Dynamic Tiling Canvas containing interactive CLI panes and preset toolbars."""

    DEFAULT_CSS = """
    DynamicWorkspace {
        width: 1fr;
        height: 100%;
        layout: vertical;
        padding: 0;
        margin: 0;
    }
    #preset-toolbar {
        height: 3;
        background: #161616;
        border-bottom: heavy #FFE135;
        padding: 0 1;
        layout: horizontal;
    }
    .preset-label {
        width: auto;
        color: #FFE135;
        text-style: bold;
        content-align: center middle;
        padding-right: 1;
    }
    .preset-btn {
        width: auto;
        min-width: 10;
        height: 1;
        margin: 0 1 0 0;
        background: #252525;
        color: #E0E0E0;
        border: none;
    }
    .preset-btn:hover {
        background: #FFE135;
        color: #000000;
        text-style: bold;
    }
    .preset-btn-active {
        background: #00FF7F;
        color: #000000;
        text-style: bold;
    }
    #workspace-canvas {
        width: 100%;
        height: 1fr;
        padding: 0;
        margin: 0;
    }
    .split-col {
        layout: horizontal;
        height: 100%;
        width: 100%;
    }
    .split-row {
        layout: vertical;
        height: 100%;
        width: 100%;
    }
    """

    def __init__(
        self,
        state: FortressState,
        event_bus: EventBus,
        plugin_manager: Optional[PluginManager] = None,
        initial_preset: str = "grid_2x2",
    ) -> None:
        super().__init__(id="right-canvas")
        self.state = state
        self.event_bus = event_bus
        self.plugin_manager = plugin_manager
        self.current_preset = initial_preset
        self._tile_counter: int = 1
        self._active_tiles: Dict[str, CliTilePane] = {}

    def compose(self) -> ComposeResult:
        # Layout Presets Quick Toolbar
        with Horizontal(id="preset-toolbar"):
            yield Static("📐 DÜZEN (LAYOUT):", classes="preset-label")
            yield Button("🔲 Tek", id="preset-single", classes="preset-btn", tooltip="Tek Tam Ekran CLI")
            yield Button("◫ 2 Sütun", id="preset-split-v", classes="preset-btn", tooltip="İki Dikey Sütun")
            yield Button("⬒ 2 Satır", id="preset-split-h", classes="preset-btn", tooltip="İki Yatay Satır")
            yield Button("⊞ 2x2 Grid", id="preset-grid-2x2", classes="preset-btn preset-btn-active", tooltip="4'lü 2x2 Izgara")
            yield Button("◰ Ana + Yan", id="preset-main-stack", classes="preset-btn", tooltip="Sol Ana + Sağ Yan Sütun")
            yield Button("⫴ 3 Sütun", id="preset-three-cols", classes="preset-btn", tooltip="Üç Dikey Sütun")
            yield Button("➕ Yeni CLI", id="preset-add-tile", classes="preset-btn", tooltip="Yeni CLI Bölmesi Ekle")

        # Dynamic Tiling Container Canvas
        yield Vertical(id="workspace-canvas")

    async def on_mount(self) -> None:
        await self.apply_preset(self.current_preset)

    def _next_tile_id(self) -> str:
        tid = f"tile_{self._tile_counter}"
        self._tile_counter += 1
        return tid

    def _create_tile(self, cli_type: str, tile_id: Optional[str] = None) -> CliTilePane:
        tid = tile_id or self._next_tile_id()
        tile = CliTilePane(
            tile_id=tid,
            cli_type=cli_type,
            state=self.state,
            event_bus=self.event_bus,
            plugin_manager=self.plugin_manager,
            on_action=self.handle_tile_action,
        )
        self._active_tiles[tid] = tile
        return tile

    async def apply_preset(self, preset_name: str) -> None:
        """Instantly rearranges workspace panes into a chosen preset layout."""
        self.current_preset = preset_name
        canvas = self.query_one("#workspace-canvas", Vertical)
        for child in list(canvas.children):
            await child.remove()
        self._active_tiles.clear()

        # Update button highlights
        for btn in self.query(".preset-btn"):
            btn.remove_class("preset-btn-active")
        try:
            active_btn = self.query_one(f"#preset-{preset_name.replace('_', '-')}", Button)
            active_btn.add_class("preset-btn-active")
        except Exception:
            pass

        if preset_name == "single":
            tile = self._create_tile("minion-01")
            await canvas.mount(tile)

        elif preset_name == "split_v":
            container = Horizontal(classes="split-col")
            t1 = self._create_tile("minion-01")
            t2 = self._create_tile("shell")
            splitter = DragSplitter(direction="horizontal")
            await canvas.mount(container)
            await container.mount(t1)
            await container.mount(splitter)
            await container.mount(t2)

        elif preset_name == "split_h":
            container = Vertical(classes="split-row")
            t1 = self._create_tile("minion-01")
            t2 = self._create_tile("error")
            splitter = DragSplitter(direction="vertical")
            await canvas.mount(container)
            await container.mount(t1)
            await container.mount(splitter)
            await container.mount(t2)

        elif preset_name == "grid_2x2":
            # 2 rows x 2 cols with horizontal and vertical drag splitters
            container = Vertical(classes="split-row")
            top_row = Horizontal(classes="split-col")
            bot_row = Horizontal(classes="split-col")
            v_splitter = DragSplitter(direction="vertical")

            t1 = self._create_tile("minion-01")
            t2 = self._create_tile("error")
            t3 = self._create_tile("sniper")
            t4 = self._create_tile("plugins")

            h_split1 = DragSplitter(direction="horizontal")
            h_split2 = DragSplitter(direction="horizontal")

            await canvas.mount(container)
            await container.mount(top_row)
            await top_row.mount(t1)
            await top_row.mount(h_split1)
            await top_row.mount(t2)

            await container.mount(v_splitter)

            await container.mount(bot_row)
            await bot_row.mount(t3)
            await bot_row.mount(h_split2)
            await bot_row.mount(t4)

        elif preset_name == "main_stack":
            main_container = Horizontal(classes="split-col")
            t1 = self._create_tile("minion-01")
            h_splitter = DragSplitter(direction="horizontal")

            right_stack = Vertical(classes="split-row")
            t2 = self._create_tile("error")
            v_splitter = DragSplitter(direction="vertical")
            t3 = self._create_tile("shell")

            await canvas.mount(main_container)
            await main_container.mount(t1)
            await main_container.mount(h_splitter)
            await main_container.mount(right_stack)
            await right_stack.mount(t2)
            await right_stack.mount(v_splitter)
            await right_stack.mount(t3)

        elif preset_name == "three_cols":
            container = Horizontal(classes="split-col")
            t1 = self._create_tile("minion-01")
            s1 = DragSplitter(direction="horizontal")
            t2 = self._create_tile("minion-02")
            s2 = DragSplitter(direction="horizontal")
            t3 = self._create_tile("shell")

            await canvas.mount(container)
            await container.mount(t1)
            await container.mount(s1)
            await container.mount(t2)
            await container.mount(s2)
            await container.mount(t3)

        self.app.notify(f"Düzen uygulandı: {preset_name}", title="LAYOUT DEĞİŞTİ", severity="information")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "preset-single":
            self.run_worker(self.apply_preset("single"))
        elif btn_id == "preset-split-v":
            self.run_worker(self.apply_preset("split_v"))
        elif btn_id == "preset-split-h":
            self.run_worker(self.apply_preset("split_h"))
        elif btn_id == "preset-grid-2x2":
            self.run_worker(self.apply_preset("grid_2x2"))
        elif btn_id == "preset-main-stack":
            self.run_worker(self.apply_preset("main_stack"))
        elif btn_id == "preset-three-cols":
            self.run_worker(self.apply_preset("three_cols"))
        elif btn_id == "preset-add-tile":
            self.run_worker(self.add_new_tile())

    async def add_new_tile(self, cli_type: str = "shell") -> None:
        """Adds a new CLI tile to the current layout."""
        canvas = self.query_one("#workspace-canvas", Vertical)
        new_tile = self._create_tile(cli_type)
        splitter = DragSplitter(direction="vertical")
        await canvas.mount(splitter)
        await canvas.mount(new_tile)
        self.app.notify(f"Yeni CLI bölmesi eklendi: [{cli_type}]", title="YENİ PENCERE")

    def handle_tile_action(self, action: str, tile_id: str, data: Dict[str, Any]) -> None:
        """Dispatches right-click and header actions from tiles."""
        if action == "split_v":
            self.run_worker(self.split_tile(tile_id, direction="horizontal"))
        elif action == "split_h":
            self.run_worker(self.split_tile(tile_id, direction="vertical"))
        elif action == "close":
            self.run_worker(self.close_tile(tile_id))
        elif action == "detach":
            cli_type = data.get("cli_type", "all")
            self.detach_tile(tile_id, cli_type)

    async def split_tile(self, tile_id: str, direction: str = "horizontal") -> None:
        """Splits an active tile either horizontally (columns) or vertically (rows)."""
        target_tile = self._active_tiles.get(tile_id)
        if not target_tile or not target_tile.parent:
            return

        parent = target_tile.parent
        cli_options = ["shell", "minion-02", "minion-03", "error", "sniper"]
        # Pick next unused CLI type
        new_cli = "shell"
        for opt in cli_options:
            if not any(t.cli_type == opt for t in self._active_tiles.values()):
                new_cli = opt
                break

        new_tile = self._create_tile(new_cli)
        splitter = DragSplitter(direction=direction)

        if direction == "horizontal":
            # If parent is already Horizontal, insert after target
            if isinstance(parent, Horizontal):
                idx = parent.children.index(target_tile)
                await parent.mount(splitter, after=idx)
                await parent.mount(new_tile, after=idx + 1)
            else:
                # Wrap target_tile and new_tile inside a new Horizontal container
                h_box = Horizontal(classes="split-col")
                idx = parent.children.index(target_tile)
                await parent.mount(h_box, after=idx)
                await target_tile.remove()
                await h_box.mount(target_tile)
                await h_box.mount(splitter)
                await h_box.mount(new_tile)
        else:
            # Vertical split
            if isinstance(parent, Vertical):
                idx = parent.children.index(target_tile)
                await parent.mount(splitter, after=idx)
                await parent.mount(new_tile, after=idx + 1)
            else:
                v_box = Vertical(classes="split-row")
                idx = parent.children.index(target_tile)
                await parent.mount(v_box, after=idx)
                await target_tile.remove()
                await v_box.mount(target_tile)
                await v_box.mount(splitter)
                await v_box.mount(new_tile)

        self.app.notify(f"Pencere bölündü: Yeni [{new_cli}] açıldı.", title="PENCERE BÖLÜNDÜ")

    async def close_tile(self, tile_id: str) -> None:
        """Closes a tile and adjusts layout."""
        if len(self._active_tiles) <= 1:
            self.app.notify("En az bir CLI bölmesi açık kalmalıdır!", severity="warning")
            return

        target_tile = self._active_tiles.pop(tile_id, None)
        if not target_tile:
            return

        parent = target_tile.parent
        await target_tile.remove()

        # Also remove adjacent splitter if any
        if parent:
            for child in list(parent.children):
                if isinstance(child, DragSplitter):
                    await child.remove()
                    break

        self.app.notify(f"CLI bölmesi kapatıldı: {tile_id}", title="KAPATILDI")

    def detach_tile(self, tile_id: str, cli_type: str) -> None:
        """Spawns an independent OS console window hosting this specific CLI."""
        root_path = Path(__file__).resolve().parent.parent.parent
        script_path = root_path / "detached_monitor.py"
        py_exec = sys.executable

        try:
            target_arg = f"--target {cli_type}"
            if os.name == "nt":
                cmd = f'start "MINION-FORTRESS: Detached [{cli_type.upper()}]" "{py_exec}" "{script_path}" {target_arg}'
                subprocess.Popen(cmd, shell=True)
            else:
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                    if shutil.which(term):
                        subprocess.Popen([term, "-e", f"{py_exec} {script_path} {target_arg}"])
                        break
                else:
                    subprocess.Popen([py_exec, str(script_path), "--target", cli_type])

            self.app.notify(
                f"🗗 [{cli_type.upper()}] bağımsız Windows penceresi olarak ayrıldı!",
                title="BİRLEŞİK DÜZENDEN AYRILDI",
                severity="information",
            )
        except Exception as e:
            self.app.notify(f"Pencere ayrılamadı: {e}", severity="error")
