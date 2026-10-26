"""
Comprehensive unit and integration tests for Dynamic Tiling Workspace,
Per-tile CLI execution, Right-Click Context Menu, DragSplitter, and Layout Presets.
"""

import pytest
from textual import events
from textual.widgets import Button, Input, Static

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
        initial_preset="grid_2x2",
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
        await pilot.pause(0.2)
        assert ws.current_preset == "single"
        assert len(ws._active_tiles) == 1

        # Test Switching to 'split_v' preset
        btn_v = ws.query_one("#preset-split-v", Button)
        btn_v.press()
        await pilot.pause(0.2)
        assert ws.current_preset == "split_v"
        assert len(ws._active_tiles) == 2

        # Test Switching to 'main_stack' preset
        btn_stack = ws.query_one("#preset-main-stack", Button)
        btn_stack.press()
        await pilot.pause(0.2)
        assert ws.current_preset == "main_stack"
        assert len(ws._active_tiles) == 3

        # Test Switching to 'three_cols' preset
        btn_3 = ws.query_one("#preset-three-cols", Button)
        btn_3.press()
        await pilot.pause(0.2)
        assert ws.current_preset == "three_cols"
        assert len(ws._active_tiles) == 3

        # Test Switching back to 'grid_2x2'
        btn_grid = ws.query_one("#preset-grid-2x2", Button)
        btn_grid.press()
        await pilot.pause(0.25)
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
        initial_preset="grid_2x2",
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
        initial_preset="grid_2x2",
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
        initial_preset="grid_2x2",
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
        initial_preset="grid_2x2",
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


@pytest.mark.asyncio
async def test_shell_execution_and_interactive_tools():
    """Verify that commands execute asynchronously without blocking, and interactive tools are handled safely."""
    state = FortressState()
    bus = EventBus()
    pane = InteractiveShellPane(state, bus)

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        tile = ws._active_tiles["tile_1"]

        # Switch tile to shell mode
        await tile.switch_cli("shell")
        await pilot.pause(0.1)

        shell_pane = tile.query_one(InteractiveShellPane)
        assert shell_pane is not None

        # Execute a quick command
        await shell_pane.execute_command("echo fortress_online")
        await pilot.pause(0.3)

        # Execute an interactive command (agy) which is safely routed without hanging
        await shell_pane.execute_command("agy --dangerously-skip-permissions")
        await pilot.pause(0.2)

        # Ensure the app is still 100% alive, responding, and unblocked
        assert app.is_running is True

        await app.action_quit()


@pytest.mark.asyncio
async def test_three_panes_paired_splitter_and_input_typing():
    """Verify paired 2-way dragging across 3 panes and instant keyboard input focus."""
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
        initial_preset="grid_2x2",
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)

        # Apply 3 columns layout preset
        await ws.apply_preset("three_cols")
        await pilot.pause(0.2)
        assert len(ws._active_tiles) == 3

        splitters = list(ws.query(DragSplitter))
        assert len(splitters) >= 2
        s1, s2 = splitters[0], splitters[1]

        # Verify adjacent pairs are correctly identified
        prev1, next1 = s1._get_adjacent_pair()
        prev2, next2 = s2._get_adjacent_pair()
        assert prev1 is not None and next1 is not None
        assert prev2 is not None and next2 is not None
        # s1's next widget is the middle tile, which is s2's previous widget!
        assert next1 == prev2

        # Simulate dragging s1: left click mouse down and move
        s1.post_message(
            events.MouseDown(
                s1,
                x=0,
                y=0,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=40,
                screen_y=10,
            )
        )
        await pilot.pause(0.05)
        assert s1.dragging is True

        initial_prev1_w = prev1.outer_size.width
        initial_next1_w = next1.outer_size.width
        comb1 = initial_prev1_w + initial_next1_w

        s1.post_message(
            events.MouseMove(
                s1,
                x=5,
                y=0,
                delta_x=5,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=45,
                screen_y=10,
            )
        )
        await pilot.pause(0.05)
        s1.post_message(
            events.MouseUp(
                s1,
                x=5,
                y=0,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=45,
                screen_y=10,
            )
        )
        await pilot.pause(0.05)

        # S1 pair exchanged width while sum remained invariant
        assert prev1.styles.width.value + next1.styles.width.value == comb1

        # Test typing directly into newly split tile input
        await ws.split_tile(prev1.tile_id, direction="vertical")
        await pilot.pause(0.2)

        # Get latest active tile
        new_tile = list(ws._active_tiles.values())[-1]
        new_tile.focus_input()
        await pilot.pause(0.1)

        tile_input = new_tile.query_one(f"#input-{new_tile.tile_id}", Input)
        assert app.focused == tile_input

        # Type command into the tile input
        await pilot.press("d", "i", "r")
        assert tile_input.value == "dir"

        await app.action_quit()


@pytest.mark.asyncio
async def test_tile_command_history_and_clipboard_paste():
    """Verify Up/Down command history navigation and clipboard paste inside a tile."""
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
        initial_preset="grid_2x2",
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        tile = list(ws._active_tiles.values())[0]
        tile_input = tile.query_one(f"#input-{tile.tile_id}", Input)
        tile.focus_input()
        await pilot.pause(0.1)

        # 1. Submit multiple commands to populate history
        tile_input.value = "status"
        tile.post_message(Input.Submitted(tile_input, value="status"))
        await pilot.pause(0.1)

        tile_input.value = "echo test_1"
        tile.post_message(Input.Submitted(tile_input, value="echo test_1"))
        await pilot.pause(0.1)

        tile_input.value = "echo test_2"
        tile.post_message(Input.Submitted(tile_input, value="echo test_2"))
        await pilot.pause(0.1)

        assert tile.history == ["status", "echo test_1", "echo test_2"]

        # 2. Test UP arrow history recall
        await pilot.press("up")
        assert tile_input.value == "echo test_2"

        await pilot.press("up")
        assert tile_input.value == "echo test_1"

        await pilot.press("up")
        assert tile_input.value == "status"

        # 3. Test DOWN arrow history navigation
        await pilot.press("down")
        assert tile_input.value == "echo test_1"

        await pilot.press("down")
        assert tile_input.value == "echo test_2"

        await pilot.press("down")
        assert tile_input.value == ""

        # 4. Test Ctrl+A select-all and Ctrl+V paste functionality into tile input
        tile_input.value = "agy --dangerously-skip-permissions"
        tile_input.cursor_position = len(tile_input.value)
        await pilot.press("ctrl+a")
        assert tile_input.selected_text == "agy --dangerously-skip-permissions"

        from unittest.mock import patch
        with patch("minion_fortress.ui.cli_input.get_clipboard_text", return_value="custom_pasted_cmd"):
            await pilot.press("ctrl+v")
            assert tile_input.value == "custom_pasted_cmd"

        # 5. Verify Context Menu has Paste button when opened
        app.push_screen(TileContextMenu(tile.tile_id, tile.cli_type))
        await pilot.pause(0.1)
        btn_paste = app.screen.query_one("#btn-paste", Button)
        assert btn_paste is not None
        assert "Yapıştır" in str(btn_paste.label)
        app.pop_screen()
        await pilot.pause(0.1)

        await app.action_quit()


@pytest.mark.asyncio
async def test_agy_agent_embedded_session():
    """Verify seamless agy agent activation, prompt updates, and exit in shell pane."""
    state = FortressState()
    bus = EventBus()

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        auto_spawn_detached=False,
    )

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        tile = ws._active_tiles["tile_1"]

        # 1. Switch to shell mode
        await tile.switch_cli("shell")
        await pilot.pause(0.1)
        prompt_lbl = tile.query_one(f"#prompt-lbl-{tile.tile_id}", Static)
        assert prompt_lbl.render().plain == "[shell]>"

        shell_pane = tile.query_one(InteractiveShellPane)
        assert shell_pane.agy_mode is False

        # 2. Enter agy mode via command
        await shell_pane.execute_command("agy --dangerously-skip-permissions")
        await pilot.pause(0.1)
        assert shell_pane.agy_mode is True
        assert prompt_lbl.render().plain == "[agy]>"

        # 3. Exit agy mode back to standard shell
        await shell_pane.execute_command("exit")
        await pilot.pause(0.1)
        assert shell_pane.agy_mode is False
        assert prompt_lbl.render().plain == "[shell]>"

        # 4. Switch directly to 'agy' CLI type
        await tile.switch_cli("agy")
        await pilot.pause(0.1)
        shell_pane_agy = tile.query_one(InteractiveShellPane)
        assert shell_pane_agy.agy_mode is True
        assert prompt_lbl.render().plain == "[agy]>"

        # 5. Check context menu has external terminal button
        app.push_screen(TileContextMenu(tile.tile_id, tile.cli_type))
        await pilot.pause(0.1)
        btn_ext = app.screen.query_one("#btn-open-ext-term", Button)
        assert btn_ext is not None
        app.pop_screen()
        await pilot.pause(0.1)

        await app.action_quit()


@pytest.mark.asyncio
async def test_richlog_wrapping_and_no_horizontal_scroll():
    """Verify that text wraps dynamically to pane width without horizontal scroll."""
    state = FortressState()
    bus = EventBus()

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        auto_spawn_detached=False,
    )

    async with app.run_test(size=(60, 25)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        tile = ws._active_tiles["tile_1"]

        # Switch to shell and verify RichLog configuration in stream view
        await tile.switch_cli("shell")
        await pilot.pause(0.1)

        shell_pane = tile.query_one(InteractiveShellPane)
        shell_pane.switch_to_stream_view()
        await pilot.pause(0.1)

        from textual.widgets import RichLog
        log = tile.query_one("#shell-stream", RichLog)
        assert log.wrap is True
        assert log.min_width == 0

        # Write a line much longer than the pane's width
        log.write("A" * 150)
        await pilot.pause(0.1)

        # Confirm zero horizontal scrolling is needed
        assert log.max_scroll_x == 0

        await app.action_quit()


@pytest.mark.asyncio
async def test_split_tile_preserves_process_and_terminal_resizes_dynamically():
    """Verify that splitting a tile preserves running terminal processes, and terminal adapts dynamically when widened."""
    state = FortressState()
    bus = EventBus()

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        auto_spawn_detached=False,
        initial_preset="single",
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        t1 = ws._active_tiles["tile_1"]

        # Switch to shell
        await t1.switch_cli("shell")
        await pilot.pause(0.1)

        shell_pane = t1.query_one(InteractiveShellPane)
        from minion_fortress.ui.panes.embedded_terminal import EmbeddedTerminalWidget
        term = shell_pane.query_one(EmbeddedTerminalWidget)
        assert term is not None

        # Add a test log line to verify log history retention
        shell_pane._write_log("TEST_PRESERVED_LINE")
        initial_cols = term.cols

        # Perform horizontal split
        await ws.split_tile("tile_1", direction="horizontal")
        await pilot.pause(0.2)

        # Confirm tile_1 is still active and shell_pane is preserved
        assert "tile_1" in ws._active_tiles
        t1_after = ws._active_tiles["tile_1"]
        shell_after = t1_after.query_one(InteractiveShellPane)
        assert shell_after is shell_pane
        assert "TEST_PRESERVED_LINE" in shell_after.log_history

        # Simulate resize / widening
        from textual.geometry import Size
        new_cols = initial_cols + 20
        term.on_resize(events.Resize(Size(new_cols, 20), Size(new_cols, 20)))
        assert term.cols == new_cols

        await app.action_quit()





@pytest.mark.asyncio
async def test_fit_all_layout_button_and_grid_distribution():
    """Verify that 'Tümünü Sığdır' button fits all active windows into optimal rows and columns."""
    state = FortressState()
    bus = EventBus()

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        auto_spawn_detached=False,
        initial_preset="single",
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        ws = app.query_one(DynamicWorkspace)
        assert ws.current_preset == "single"
        assert len(ws._active_tiles) == 1

        # 1. Click '🗖 Tümünü Sığdır' button in the preset toolbar
        btn_fit_preset = ws.query_one("#preset-fit-all", Button)
        assert btn_fit_preset is not None
        btn_fit_preset.press()
        await pilot.pause(0.25)

        assert ws.current_preset == "fit_all"
        # Fits all 5 core panes (minion-01, shell, error, sniper, plugins)
        assert len(ws._active_tiles) == 5
        active_types = [t.cli_type for t in ws._active_tiles.values()]
        assert "minion-01" in active_types
        assert "shell" in active_types
        assert "error" in active_types
        assert "sniper" in active_types
        assert "plugins" in active_types

        # Verify splitters are mounted between columns and rows
        from minion_fortress.ui.drag_splitter import DragSplitter
        splitters = list(ws.query(DragSplitter))
        assert len(splitters) >= 4  # 1 vertical row splitter + horizontal col splitters

        # 2. Switch back to single, then test sidebar button '🗖 Tümünü Sığdır (Grid)'
        btn_single = ws.query_one("#preset-single", Button)
        btn_single.press()
        await pilot.pause(0.2)
        assert len(ws._active_tiles) == 1

        btn_fit_sidebar = app.query_one("#tab-btn-fit-all", Button)
        assert btn_fit_sidebar is not None
        btn_fit_sidebar.press()
        await pilot.pause(0.25)
        assert ws.current_preset == "fit_all"
        assert len(ws._active_tiles) == 5
        assert "sidebar-tab-active" in btn_fit_sidebar.classes

        # 3. Test F9 hotkey trigger
        btn_single.press()
        await pilot.pause(0.2)
        assert len(ws._active_tiles) == 1

        await pilot.press("f9")
        await pilot.pause(0.25)
        assert ws.current_preset == "fit_all"
        assert len(ws._active_tiles) == 5

        await app.action_quit()
