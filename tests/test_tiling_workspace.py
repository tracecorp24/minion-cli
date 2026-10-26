"""
Comprehensive unit and integration tests for Dynamic Tiling Workspace,
Per-tile CLI execution, Right-Click Context Menu, DragSplitter, and Layout Presets.
"""

import pytest
from textual import events
from textual.widgets import Button, Input

from minion_fortress.core.state import FortressState, MinionStatus
from minion_fortress.core.event_bus import EventBus
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.app import MinionFortressApp
from minion_fortress.ui.workspace import DynamicWorkspace
from minion_fortress.ui.cli_tile import CliTilePane
from minion_fortress.ui.drag_splitter import DragSplitter
from minion_fortress.ui.context_menu import TileContextMenu, CliSelectorModal
from minion_fortress.ui.panes.shell_pane import InteractiveShellPane


@pytest.mark.asyncio
async def test_dynamic_workspace_presets():
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        ws = app.query_one(DynamicWorkspace)
        assert ws is not None
        # Default preset is grid_2x2 with 4 tiles
        assert len(ws._active_tiles) == 4

        # Test Switching to 'single' preset
        btn_single = ws.query_one("#preset-single", Button)
        btn_single.press()
        await pilot.pause(0.1)
        assert ws.current_preset == "single"
        assert len(ws._active_tiles) == 1

        # Test Switching to 'split_v' preset
        btn_v = ws.query_one("#preset-split-v", Button)
        btn_v.press()
        await pilot.pause(0.1)
        assert ws.current_preset == "split_v"
        assert len(ws._active_tiles) == 2

        # Test Switching to 'main_stack' preset
        btn_stack = ws.query_one("#preset-main-stack", Button)
        btn_stack.press()
        await pilot.pause(0.1)
        assert ws.current_preset == "main_stack"
        assert len(ws._active_tiles) == 3

        # Test Switching to 'three_cols' preset
        btn_3 = ws.query_one("#preset-three-cols", Button)
        btn_3.press()
        await pilot.pause(0.1)
        assert ws.current_preset == "three_cols"
        assert len(ws._active_tiles) == 3

        # Test Switching back to 'grid_2x2'
        btn_grid = ws.query_one("#preset-grid-2x2", Button)
        btn_grid.press()
        await pilot.pause(0.1)
        assert ws.current_preset == "grid_2x2"
        assert len(ws._active_tiles) == 4

        await app.action_quit()


@pytest.mark.asyncio
async def test_right_click_context_menu_and_actions():
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        ws = app.query_one(DynamicWorkspace)
        first_tile_id = list(ws._active_tiles.keys())[0]
        first_tile = ws._active_tiles[first_tile_id]

        # Simulate right-click (button=3) on the tile
        first_tile.post_message(
            events.Click(
                first_tile,
                x=5,
                y=5,
                delta_x=0,
                delta_y=0,
                button=3,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=10,
                screen_y=10,
            )
        )
        await pilot.pause(0.1)

        # Context menu should now be mounted on screen
        assert isinstance(app.screen, TileContextMenu)

        # Press 'Cancel'
        btn_cancel = app.screen.query_one("#btn-cancel", Button)
        btn_cancel.press()
        await pilot.pause(0.1)
        assert not isinstance(app.screen, TileContextMenu)

        # Now test Vertical Split action
        initial_tile_count = len(ws._active_tiles)
        await ws.split_tile(first_tile_id, direction="horizontal")
        await pilot.pause(0.1)
        assert len(ws._active_tiles) == initial_tile_count + 1

        # Now test Close tile action
        new_tile_id = list(ws._active_tiles.keys())[-1]
        await ws.close_tile(new_tile_id)
        await pilot.pause(0.1)
        assert len(ws._active_tiles) == initial_tile_count

        await app.action_quit()


@pytest.mark.asyncio
async def test_tile_cli_switch():
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        ws = app.query_one(DynamicWorkspace)
        first_tile_id = list(ws._active_tiles.keys())[0]
        tile = ws._active_tiles[first_tile_id]

        # Initially minion-01
        assert tile.cli_type == "minion-01"

        # Switch to shell
        await tile.switch_cli("shell")
        await pilot.pause(0.1)
        assert tile.cli_type == "shell"
        assert isinstance(tile._current_widget, InteractiveShellPane)

        # Switch to minion-03
        await tile.switch_cli("minion-03")
        await pilot.pause(0.1)
        assert tile.cli_type == "minion-03"

        await app.action_quit()


@pytest.mark.asyncio
async def test_drag_splitter_resizing():
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        ws = app.query_one(DynamicWorkspace)
        # Find horizontal splitter in grid
        splitters = list(ws.query(DragSplitter))
        assert len(splitters) >= 1

        splitter = splitters[0]
        # Simulate dragging left mouse button
        splitter.post_message(
            events.MouseDown(
                splitter,
                x=0,
                y=0,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=40,
                screen_y=15,
            )
        )
        await pilot.pause(0.05)
        assert splitter.dragging is True

        # Move mouse
        splitter.post_message(
            events.MouseMove(
                splitter,
                x=10,
                y=0,
                delta_x=10,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=50,
                screen_y=15,
            )
        )
        await pilot.pause(0.05)

        # Release mouse
        splitter.post_message(
            events.MouseUp(
                splitter,
                x=10,
                y=0,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=50,
                screen_y=15,
            )
        )
        await pilot.pause(0.05)
        assert splitter.dragging is False

        await app.action_quit()


@pytest.mark.asyncio
async def test_splits_do_not_collapse_terminals():
    """Verify that multiple horizontal and vertical splits never collapse sibling tiles or terminals."""
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
        auto_spawn_detached=False,
    )

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)

        # 1. Split tile_1 horizontally (columns)
        await ws.split_tile("tile_1", direction="horizontal")
        await pilot.pause(0.2)

        # 2. Split tile_1 vertically (rows)
        await ws.split_tile("tile_1", direction="vertical")
        await pilot.pause(0.2)

        # 3. Split tile_2 vertically (rows)
        await ws.split_tile("tile_2", direction="vertical")
        await pilot.pause(0.2)

        # 4. Split tile_3 horizontally (columns)
        await ws.split_tile("tile_3", direction="horizontal")
        await pilot.pause(0.2)

        # Check all tiles
        assert len(ws._active_tiles) == 8
        for tid, t in ws._active_tiles.items():
            assert t.size.width > 0, f"Tile {tid} ({t.cli_type}) has collapsed width: {t.size.width}"
            assert t.size.height > 0, f"Tile {tid} ({t.cli_type}) has collapsed height: {t.size.height}"

        await app.action_quit()
