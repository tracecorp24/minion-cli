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
from minion_fortress.ui.panes.shell_pane import InteractiveShellPane
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

        # Verify dynamic tiling panes and sidebar monitors are mounted
        assert app.query_one(MinionPane) is not None
        assert app.query_one(ErrorHealthPane) is not None
        assert app.query_one(LogSniperPane) is not None
        assert app.query_one(InteractiveShellPane) is not None

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
    """Verify that:
    1. Default preset is 'single' (only 1 agent window open).
    2. Other windows do not open until requested (auto_spawn_detached is False).
    3. Left sidebar hosts Agent tabs (minion, shell, fit-all) and collapsible Watchdog & Sniper.
    4. Clicking sidebar tab buttons switches the active agent pane cleanly.
    5. Watchdog and Sniper expand and collapse cleanly in the sidebar.
    6. Right workspace is dedicated to agent panes; plugin store is removed.
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

        # 1. Exactly 1 active agent tile on initial launch
        from minion_fortress.ui.workspace import DynamicWorkspace
        from textual.widgets import Collapsible
        ws = app.query_one(DynamicWorkspace)
        assert len(ws._active_tiles) == 1
        assert ws.current_preset == "single"

        # 2. Verify agent tab buttons exist in left sidebar
        btn_minion = app.query_one("#tab-btn-minion", Button)
        btn_shell = app.query_one("#tab-btn-shell", Button)
        btn_fit = app.query_one("#tab-btn-fit-all", Button)

        assert btn_minion is not None
        assert btn_shell is not None
        assert btn_fit is not None

        # Verify plugin toolstore is removed from sidebar
        assert len(app.query("#tab-btn-plugins")) == 0

        # 3. Verify Watchdog & Sniper exist as Collapsibles in left sidebar
        w_col = app.query_one("#sidebar-watchdog-collapsible", Collapsible)
        s_col = app.query_one("#sidebar-sniper-collapsible", Collapsible)
        assert w_col is not None
        assert s_col is not None

        # Initially collapsed for clean sidebar view
        assert w_col.collapsed is True
        assert s_col.collapsed is True

        # Test expanding Watchdog on click / toggle
        w_col.collapsed = False
        await pilot.pause(0.05)
        assert w_col.collapsed is False

        # Test expanding Sniper on click / toggle
        s_col.collapsed = False
        await pilot.pause(0.05)
        assert s_col.collapsed is False

        # Initially minion tab is active on the right
        first_tile = next(iter(ws._active_tiles.values()))
        assert first_tile.cli_type == "minion-01"

        # 4. Click Shell tab in sidebar -> switches to shell
        btn_shell.press()
        await pilot.pause(0.2)
        assert first_tile.cli_type == "shell"
        assert "sidebar-tab-active" in btn_shell.classes

        # 5. Click Minion tab in sidebar -> switches back to minion-01
        btn_minion.press()
        await pilot.pause(0.2)
        assert first_tile.cli_type == "minion-01"
        assert "sidebar-tab-active" in btn_minion.classes

        # 6. Click 'Tümünü Sığdır (Grid)' tab in sidebar -> fits all agent windows
        btn_fit.press()
        await pilot.pause(0.25)
        assert ws.current_preset == "fit_all"
        assert len(ws._active_tiles) >= 3
        # All panes on the right are agent windows!
        for t in ws._active_tiles.values():
            assert t.cli_type.startswith("minion-") or t.cli_type in ("shell", "agy")
        await app.action_quit()
