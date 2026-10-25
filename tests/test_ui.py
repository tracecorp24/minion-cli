"""
Textual UI Pilot Test for Minion Fortress v3.0.
Simulates App lifecycle, REPL commands, Banana Mode (F12), Export (F8),
and Time Travel interactions.
"""

import pytest
from minion_fortress.core.state import FortressState, MinionStatus
from minion_fortress.core.event_bus import EventBus
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.app import MinionFortressApp
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

    app = MinionFortressApp(state=state, event_bus=bus, daemon=daemon, plugin_manager=plugin_mgr)

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
