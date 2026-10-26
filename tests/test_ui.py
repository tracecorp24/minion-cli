"""
Textual UI Pilot Test for Minion Fortress v3.0.
Simulates App lifecycle, REPL commands, Banana Mode (F12), Export (F8),
Time Travel interactions, and Detached Monitor Window lifecycle.
"""

import pytest
from minion_fortress.core.state import FortressState, MinionStatus
from minion_fortress.core.event_bus import EventBus
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.app import MinionFortressApp
from minion_fortress.ui.detached_window import DetachedMonitorApp
from minion_fortress.ui.panes.minion_pane import MinionPane
from minion_fortress.ui.panes.error_pane import ErrorHealthPane
from minion_fortress.ui.panes.sniper_pane import LogSniperPane
from minion_fortress.ui.panes.plugin_pane import PluginPane
from textual.widgets import Input, Button


@pytest.mark.asyncio
async def test_ui_lifecycle_and_panes():
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

        # Verify all 4 dynamic tiling panes are mounted
        assert app.query_one(MinionPane) is not None
        assert app.query_one(ErrorHealthPane) is not None
        assert app.query_one(LogSniperPane) is not None
        assert app.query_one(PluginPane) is not None

        # Test Banana Mode hotkey F12
        await pilot.press("f12")
        await pilot.pause(0.1)
        assert state.banana_mode is True

        # Toggle Banana Mode off
        await pilot.press("f12")
        await pilot.pause(0.1)
        assert state.banana_mode is False

        # Test Session Export hotkey F8
        await pilot.press("f8")
        await pilot.pause(0.1)

        # Test REPL Command: Pause minion-01
        repl_input = app.query_one("#repl-input", Input)
        repl_input.value = "@01 pause"
        await app.on_input_submitted(Input.Submitted(repl_input, "@01 pause"))
        assert state.minions["01"].status == MinionStatus.PAUSED

        # Test REPL Command: Resume minion-01
        repl_input.value = "@01 resume"
        await app.on_input_submitted(Input.Submitted(repl_input, "@01 resume"))
        assert state.minions["01"].status == MinionStatus.RUNNING

        # Test Time Travel buttons (Step-by-step and rewind)
        minion_pane = app.query_one(MinionPane)
        btn_prev = minion_pane.query_one("#btn-replay-prev", Button)
        btn_prev.press()
        await pilot.pause(0.1)
        assert minion_pane.is_replay_mode is True

        btn_replay_10 = minion_pane.query_one("#btn-replay-10", Button)
        btn_replay_10.press()
        await pilot.pause(0.1)
        assert minion_pane.is_replay_mode is True

        btn_live = minion_pane.query_one("#btn-live", Button)
        btn_live.press()
        await pilot.pause(0.1)
        assert minion_pane.is_replay_mode is False

        # Test Sniper Regex Input
        sniper_input = app.query_one("#sniper-regex-input", Input)
        sniper_input.value = "AST"
        await pilot.pause(0.1)
        sniper_pane = app.query_one(LogSniperPane)
        assert sniper_pane.current_pattern == "AST"

        # Clean shutdown
        await app.action_quit()


@pytest.mark.asyncio
async def test_detached_monitor_app():
    """Verify DetachedMonitorApp mounts properly and responds to events."""
    monitor = DetachedMonitorApp(port=42099)
    async with monitor.run_test() as pilot:
        await pilot.pause(0.1)
        assert monitor.query_one("#detached-banner") is not None
        assert monitor.query_one("#error-stream") is not None
        assert monitor.query_one("#activity-stream") is not None
        monitor.exit()


@pytest.mark.asyncio
async def test_sidebar_tabs_and_single_initial_window():
    """Verify that on initial startup:
    1. Default preset is 'single' (only 1 window/pane open).
    2. Other windows do not open until requested (auto_spawn_detached is False).
    3. Left sidebar hosts all tab types (minion, shell, error, sniper, plugins).
    4. Clicking sidebar tab buttons switches the active pane cleanly.
    5. Mockup text streaming is disabled (no mock worker loops).
    """
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    assert daemon.simulate_mock is False

    app = MinionFortressApp(
        state=state,
        event_bus=bus,
        daemon=daemon,
        plugin_manager=plugin_mgr,
    )

    assert app.auto_spawn_detached is False
    assert app.initial_preset == "single"

    async with app.run_test() as pilot:
        await pilot.pause(0.2)

        # 1. Exactly 1 active tile on initial launch
        from minion_fortress.ui.workspace import DynamicWorkspace
        ws = app.query_one(DynamicWorkspace)
        assert len(ws._active_tiles) == 1
        assert ws.current_preset == "single"

        # 2. Verify all tab buttons exist in left sidebar
        btn_minion = app.query_one("#tab-btn-minion", Button)
        btn_shell = app.query_one("#tab-btn-shell", Button)
        btn_error = app.query_one("#tab-btn-error", Button)
        btn_sniper = app.query_one("#tab-btn-sniper", Button)
        btn_plugins = app.query_one("#tab-btn-plugins", Button)

        assert btn_minion is not None
        assert btn_shell is not None
        assert btn_error is not None
        assert btn_sniper is not None
        assert btn_plugins is not None

        # Initially minion tab is active
        first_tile = next(iter(ws._active_tiles.values()))
        assert first_tile.cli_type == "minion-01"

        # 3. Click Shell tab in sidebar -> switches to shell
        btn_shell.press()
        await pilot.pause(0.1)
        assert first_tile.cli_type == "shell"
        assert "sidebar-tab-active" in btn_shell.classes

        # 4. Click Error tab in sidebar -> switches to error
        btn_error.press()
        await pilot.pause(0.1)
        assert first_tile.cli_type == "error"
        assert "sidebar-tab-active" in btn_error.classes

        # 5. Click Sniper tab in sidebar -> switches to sniper
        btn_sniper.press()
        await pilot.pause(0.1)
        assert first_tile.cli_type == "sniper"
        assert "sidebar-tab-active" in btn_sniper.classes

        # 6. Click Plugins tab in sidebar -> switches to plugins
        btn_plugins.press()
        await pilot.pause(0.1)
        assert first_tile.cli_type == "plugins"
        assert "sidebar-tab-active" in btn_plugins.classes

        # 7. Still only 1 window/tile open - other windows did NOT open!
        assert len(ws._active_tiles) == 1

        # Clean exit
        await app.action_quit()
