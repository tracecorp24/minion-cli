"""
Comprehensive Test Suite for MINION-FORTRESS (KOVAN-X) v3.0.
Validates State, RingBuffer, EventBus, Bidirectional IPC Broadcast,
Plugins, Watchdog Auto-Healing (including IDLE immunity),
Banana Mode, and Snapshot Exporting.
"""

import asyncio
import os
import json
import time
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


@pytest.mark.asyncio
async def test_ipc_broadcast_to_detached_window():
    """Validates that EventBus broadcasts events to detached window clients over TCP."""
    bus = EventBus()
    test_port = 42025
    await bus.start(port=test_port)

    # Connect mock detached window client
    reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
    await asyncio.sleep(0.05)

    # Publish an event from core daemon
    test_event = Event(type=EventType.LOG, data={"source": "test-runner", "level": "WARN", "message": "IPC Detached Test"})
    bus.publish_nowait(test_event)

    # Read line on detached window client
    line = await asyncio.wait_for(reader.readline(), timeout=2.0)
    data = json.loads(line.decode("utf-8").strip())

    assert data["type"] == "LOG"
    assert data["data"]["message"] == "IPC Detached Test"

    writer.close()
    await writer.wait_closed()
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
async def test_plugin_change_event_broadcast():
    bus = EventBus()
    plugin_events = []
    bus.subscribe(EventType.PLUGIN_CHANGE, lambda e: plugin_events.append(e))
    await bus.start()

    mgr = PluginManager(event_bus=bus)
    mgr.toggle_plugin("Docling-v2")

    await asyncio.sleep(0.1)
    assert len(plugin_events) >= 1
    assert plugin_events[0].data["name"] == "Docling-v2"
    assert plugin_events[0].data["is_active"] is False

    await bus.stop()


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


@pytest.mark.asyncio
async def test_watchdog_does_not_heal_idle_minions():
    """Verify that IDLE minions are NOT killed or forced to heal by watchdog timeout."""
    state = FortressState()
    bus = EventBus()
    plugin_mgr = PluginManager()
    daemon = MinionDaemon(state, bus, plugin_mgr)

    minion2 = state.minions["02"]
    assert minion2.status == MinionStatus.IDLE

    # Age heartbeat to simulate >5 seconds overdue
    minion2.last_heartbeat = time.time() - 20.0

    # Run one watchdog inspection iteration
    now = time.time()
    for mid, minion in list(state.minions.items()):
        if minion.status in (MinionStatus.PAUSED, MinionStatus.HEALING, MinionStatus.IDLE):
            continue
        if minion.status == MinionStatus.ERROR or (now - minion.last_heartbeat) > 5.0:
            await daemon._heal_minion(mid, reason="Test overdue")

    # Minion 02 MUST remain IDLE
    assert minion2.status == MinionStatus.IDLE


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


def test_telegram_plugin_execute():
    from minion_fortress.plugins.telegram_tool import TelegramPlugin
    tg = TelegramPlugin()
    assert tg.is_active is False

    # Execute while paused
    res_paused = tg.execute({"alert": "Test failure"})
    assert res_paused["status"] == "skipped"

    # Toggle active and execute
    tg.toggle()
    assert tg.is_active is True
    res_active = tg.execute({"title": "CRITICAL", "alert": "High RAM threshold"})
    assert res_active["status"] == "sent"
    assert res_active["title"] == "CRITICAL"


def test_plugin_fuzzy_toggle():
    mgr = PluginManager()

    # Toggle with lowercase partial name
    assert mgr.get_plugin("Docling-v2").is_active is True
    res = mgr.toggle_plugin("docling")
    assert res is False
    assert mgr.get_plugin("Docling-v2").is_active is False

    # Toggle back
    res2 = mgr.toggle_plugin("Docling-v2")
    assert res2 is True
    assert mgr.get_plugin("Docling-v2").is_active is True


def test_history_snapshots_replay():
    m = MinionState(id="01", name="ast-parser", progress=25, current_task="Task A")
    m.record_snapshot()
    m.progress = 50
    m.current_task = "Task B"
    m.record_snapshot()

    assert len(m.history_snapshots) == 2
    snaps = m.history_snapshots.replay(1)
    assert len(snaps) == 1
    assert snaps[0]["progress"] == 50
    assert snaps[0]["current_task"] == "Task B"

