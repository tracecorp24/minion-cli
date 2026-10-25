"""
Comprehensive Test Suite for MINION-FORTRESS (KOVAN-X) v3.0.
Validates State, RingBuffer, EventBus, Plugins, Watchdog Auto-Healing,
Banana Mode, and Snapshot Exporting.
"""

import asyncio
import os
import json
import pytest
from pathlib import Path

from minion_fortress.core.state import RingBuffer, FortressState, MinionState, MinionStatus, LogEntry
from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager


def test_ring_buffer_operations():
    rb = RingBuffer[int](maxlen=5)
    for i in range(10):
        rb.append(i)

    # Maxlen bounding
    assert len(rb) == 5
    assert rb.get_all() == [5, 6, 7, 8, 9]

    # Replay functionality (Feature 6: Time Travel)
    assert rb.replay(3) == [7, 8, 9]
    assert rb.replay(10) == [5, 6, 7, 8, 9]


def test_state_and_snapshot_export(tmp_path: Path):
    state = FortressState()
    assert state.get_active_minion_count() == 0

    m1 = MinionState(id="01", name="ast-parser", status=MinionStatus.RUNNING)
    m1.add_log("INFO", "Initial test log")
    state.minions["01"] = m1

    assert state.get_active_minion_count() == 1
    assert state.get_total_minion_count() == 1

    # Export snapshot to markdown & json (Feature 9)
    md_file, json_file = state.export_snapshot(tmp_path)
    assert md_file.exists()
    assert json_file.exists()

    md_text = md_file.read_text(encoding="utf-8")
    assert "MINION-FORTRESS" in md_text
    assert "ast-parser" in md_text

    with open(json_file, "r", encoding="utf-8") as jf:
        data = json.load(jf)
    assert data["telemetry"]["active_minions"] == 1
    assert "01" in data["minions"]


@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    received_events = []

    def log_handler(event: Event):
        received_events.append(event)

    bus.subscribe(EventType.LOG, log_handler)
    await bus.start()

    ev = Event(type=EventType.LOG, data={"message": "Test event dispatch"})
    bus.publish_nowait(ev)

    await asyncio.sleep(0.1)
    assert len(received_events) >= 1
    assert received_events[0].data["message"] == "Test event dispatch"

    await bus.stop()


def test_plugin_manager():
    mgr = PluginManager()
    plugins = mgr.get_all()
    assert "Docling-v2" in plugins
    assert "pgvector-sync" in plugins
    assert "Telegram-Bot" in plugins
    assert "OpenRouter-API" in plugins

    # Verify initial states from plan
    docling = mgr.get_plugin("Docling-v2")
    assert docling.is_active is True

    telegram = mgr.get_plugin("Telegram-Bot")
    assert telegram.is_active is False

    # Test toggle
    new_st = mgr.toggle_plugin("Telegram-Bot")
    assert new_st is True
    assert telegram.is_active is True

    new_st2 = mgr.toggle_plugin("Telegram-Bot")
    assert new_st2 is False
    assert telegram.is_active is False


@pytest.mark.asyncio
async def test_watchdog_auto_healing():
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    await bus.start()

    # Verify initial minions populated
    assert "01" in state.minions
    minion1 = state.minions["01"]
    assert minion1.status == MinionStatus.RUNNING

    # Inject fatal fault to trigger watchdog
    daemon.trigger_test_error("01")
    assert minion1.status == MinionStatus.ERROR

    # Execute auto-healing
    await daemon._heal_minion("01", reason="Test auto-heal", delay=0.01)
    assert minion1.status == MinionStatus.RUNNING
    assert "Auto-healing complete" in minion1.current_task

    await bus.stop()


def test_banana_mode(tmp_path: Path):
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    assert state.banana_mode is False

    # Trigger Banana Mode (Emergency Panic)
    is_banana = daemon.toggle_banana_mode()
    assert is_banana is True
    assert state.banana_mode is True

    # Untoggle
    is_banana_off = daemon.toggle_banana_mode()
    assert is_banana_off is False
    assert state.banana_mode is False
