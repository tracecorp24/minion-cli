"""
Minion Daemon Engine and Auto-Healing Watchdog (Feature 8 & Architecture Core).
Orchestrates agent pools, task pipelines, heartbeat monitoring, and automatic
fault recovery with zero UI lag.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.core.state import FortressState, MinionState, MinionStatus, LogEntry
from minion_fortress.plugins.manager import PluginManager

logger = logging.getLogger("MinionDaemon")


class MinionDaemon:
    """Core daemon managing minion execution, telemetry, and Watchdog self-healing."""

    def __init__(self, state: FortressState, event_bus: EventBus, plugin_manager: PluginManager) -> None:
        self.state = state
        self.event_bus = event_bus
        self.plugin_manager = plugin_manager
        self.running: bool = False
        self._tasks: List[asyncio.Task] = []
        self._init_minions()

    def _init_minions(self) -> None:
        """Initializes default minions matching Minion Fortress v3.0 plan."""
        initial_configs = [
            ("01", "ast-parser", MinionStatus.RUNNING, "qwen-2.5-coder", "Mapping AST syntax trees (Node #142)"),
            ("02", "net-mon", MinionStatus.IDLE, "glm-4-flash", "Awaiting socket stream traffic"),
            ("03", "quant", MinionStatus.BUSY, "deepseek-r1", "Computing FP8 quantization tensors"),
            ("04", "doc-ext", MinionStatus.PAUSED, "qwen-2.5-coder", "Standby for incoming PDF/markdown docs"),
            ("05", "code-synth", MinionStatus.RUNNING, "qwen-2.5-coder", "Generating unit test coverage"),
        ]

        for mid, name, status, model, task in initial_configs:
            minion = MinionState(
                id=mid,
                name=name,
                status=status,
                model=model,
                current_task=task,
                cpu=12.0 if status == MinionStatus.RUNNING else (45.0 if status == MinionStatus.BUSY else 0.5),
                memory_mb=round(random.uniform(220.0, 580.0), 1),
                progress=random.randint(40, 85) if status != MinionStatus.IDLE else 0,
            )
            entry = minion.add_log("INFO", f"Minion worker initialized [PID: {os.getpid()}]")
            self.state.minions[mid] = minion
            self.state.add_global_log("INFO", f"minion-{mid}", f"Worker registered: {name} ({model})")

    async def start(self) -> None:
        """Starts worker simulator, telemetry loop, and Watchdog self-healer."""
        self.running = True
        self._tasks.append(asyncio.create_task(self._worker_loop()))
        self._tasks.append(asyncio.create_task(self._telemetry_loop()))
        self._tasks.append(asyncio.create_task(self._watchdog_loop()))
        self._tasks.append(asyncio.create_task(self._periodic_anomaly_loop()))

    async def stop(self) -> None:
        """Gracefully halts daemon."""
        self.running = False
        for t in self._tasks:
            t.cancel()

    async def _worker_loop(self) -> None:
        """Simulates realistic asynchronous minion work pipelines."""
        task_cycles = {
            "01": [
                "AST Nodes mapped: 142",
                "AST Syntax tree validation complete",
                "Resolving import dependencies in package",
                "Extracting Python class signatures",
                "Generating AST bytecode cache",
            ],
            "02": [
                "Polling API gateway latency (18ms)",
                "Unix socket buffer clear: 0 backlog",
                "IPC heartbeat ACK received from workers",
                "Network throughput stable: 4.2 MB/s",
            ],
            "03": [
                "Matrix multiplication pass 4/8",
                "Computing FP8 quantization tensor scale",
                "VRAM allocation verified: 18.4 GB",
                "Quantization tensor layer #42 synchronized",
            ],
            "04": [
                "Docling-v2 OCR layout scan in progress",
                "Extracting 3 markdown tables from specification",
                "Vectorizing text chunk #84",
                "Batch dispatched to pgvector-sync",
            ],
            "05": [
                "Running pytest coverage for core modules",
                "Synthesizing unit test test_event_bus.py",
                "Code coverage reached: 94.2%",
                "Commit candidate staged for validation",
            ],
        }

        while self.running:
            await asyncio.sleep(1.2)
            if self.state.banana_mode:
                # Banana mode pauses all active processing
                continue

            for mid, minion in list(self.state.minions.items()):
                if minion.status not in (MinionStatus.RUNNING, MinionStatus.BUSY):
                    continue

                # Update heartbeat
                minion.last_heartbeat = time.time()

                # Progress increment
                minion.progress += random.randint(3, 8)
                if minion.progress >= 100:
                    minion.progress = 0
                    self.state.completed_tasks += 1
                    self.state.token_cost += random.uniform(0.0008, 0.0025)

                # CPU oscillation
                if minion.status == MinionStatus.BUSY:
                    minion.cpu = round(random.uniform(40.0, 75.0), 1)
                else:
                    minion.cpu = round(random.uniform(8.0, 28.0), 1)

                # Update task text
                choices = task_cycles.get(mid, ["Processing task stream"])
                new_task = random.choice(choices)
                minion.current_task = f"{new_task} [{minion.progress}%]"
                minion.record_snapshot()

                # Log entry
                log_entry = minion.add_log("INFO", f"> {minion.current_task}")
                self.state.add_global_log("INFO", f"minion-{mid}", minion.current_task)

                # Publish event
                self.event_bus.publish_nowait(
                    Event(
                        type=EventType.LOG,
                        data={
                            "source": f"minion-{mid}",
                            "level": "INFO",
                            "message": minion.current_task,
                            "minion_id": mid,
                            "progress": minion.progress,
                            "cpu": minion.cpu,
                        },
                    )
                )

    async def _telemetry_loop(self) -> None:
        """Publishes system metrics to the event bus every 2 seconds."""
        while self.running:
            await asyncio.sleep(2.0)
            self.event_bus.publish_nowait(
                Event(
                    type=EventType.TELEMETRY,
                    data={
                        "total_tasks": self.state.total_tasks,
                        "completed_tasks": self.state.completed_tasks,
                        "token_cost": self.state.token_cost,
                        "active_minions": self.state.get_active_minion_count(),
                        "banana_mode": self.state.banana_mode,
                    },
                )
            )

    async def _watchdog_loop(self) -> None:
        """
        Feature 8: Auto-Healing Shield & Watchdog.
        Monitors minion heartbeats. If a minion has not pulsed within 5 seconds
        or is stuck in ERROR state, triggers auto-healing:
        terminates faulty state and respawns cleanly.
        """
        while self.running:
            await asyncio.sleep(1.0)
            if self.state.banana_mode:
                continue

            now = time.time()
            for mid, minion in list(self.state.minions.items()):
                # Check for frozen heartbeat or ERROR state
                overdue = (now - minion.last_heartbeat) > 5.0
                is_error = minion.status == MinionStatus.ERROR

                if (overdue or is_error) and minion.status not in (MinionStatus.PAUSED, MinionStatus.HEALING):
                    await self._heal_minion(mid, reason="Heartbeat timeout (>5s)" if overdue else "Fatal error trigger")

    async def _heal_minion(self, minion_id: str, reason: str, delay: float = 1.5) -> None:
        """Executes auto-healing sequence for a minion."""
        minion = self.state.minions.get(minion_id)
        if not minion:
            return

        minion.status = MinionStatus.HEALING
        heal_msg = f"🛡️ WATCHDOG DETECTED FAULT on [{minion.name} (ID: {minion_id})]: {reason}. Initiating Auto-Healing..."
        self.state.add_global_log("HEAL", "watchdog", heal_msg)
        self.event_bus.publish_nowait(
            Event(
                type=EventType.ERROR,
                data={"source": "watchdog", "level": "HEAL", "message": heal_msg, "minion_id": minion_id},
            )
        )

        # Non-blocking auto-heal delay
        if delay > 0:
            await asyncio.sleep(delay)

        # Reset clean state
        minion.status = MinionStatus.RUNNING
        minion.last_heartbeat = time.time()
        minion.cpu = round(random.uniform(10.0, 20.0), 1)
        minion.progress = 10
        minion.current_task = "Auto-healing complete. Task queue resumed cleanly."
        minion.add_log("HEAL", "Worker respawned with clean state.")

        recovered_msg = f"✅ Auto-Healing complete: minion-{minion_id} ({minion.name}) restored to RUNNING."
        self.state.add_global_log("HEAL", "watchdog", recovered_msg)
        self.event_bus.publish_nowait(
            Event(
                type=EventType.LOG,
                data={"source": "watchdog", "level": "HEAL", "message": recovered_msg, "minion_id": minion_id},
            )
        )

    async def _periodic_anomaly_loop(self) -> None:
        """
        Periodically simulates real-world events (HTTP 429, DB timeout, RAM threshold)
        to populate the Error & Health Monitor (Feature 2) and verify live filters.
        """
        anomalies = [
            ("WARN", "RAM usage threshold alert: >82% allocated on cluster pool"),
            ("ERROR", "OpenRouter API 429: Rate limit exceeded, backing off for 1200ms"),
            ("WARN", "Network latency spike on pgvector socket: 142ms"),
            ("ERROR", "HTTP 500: Upstream Model Gateway temporary timeout"),
            ("WARN", "GPU VRAM warning: Node 0 approaching 19.1 GB allocation"),
        ]

        while self.running:
            await asyncio.sleep(12.0)
            if self.state.banana_mode:
                continue

            level, msg = random.choice(anomalies)
            src = random.choice(["api-gw", "db-vector", "cluster-telemetry", "minion-03"])
            self.state.add_global_log(level, src, msg)
            self.event_bus.publish_nowait(
                Event(
                    type=EventType.ERROR if level == "ERROR" else EventType.LOG,
                    data={"source": src, "level": level, "message": msg},
                )
            )

    # REPL and UI Control methods
    def toggle_banana_mode(self) -> bool:
        """
        Extra Feature: Banana Mode (Emergency Panic Button).
        Freezes processing, flushes current state to disk, and triggers warning banner.
        """
        self.state.banana_mode = not self.state.banana_mode
        if self.state.banana_mode:
            panic_dir = Path("reports")
            panic_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            panic_file = panic_dir / f"banana_panic_lockdown_{ts}.json"
            with open(panic_file, "w", encoding="utf-8") as pf:
                json.dump({"banana_mode": True, "timestamp": time.time(), "status": "LOCKED"}, pf, indent=2)

            msg = "🍌 BANANA MODE ACTIVATED! Cluster frozen in emergency lockdown. State persisted."
            self.state.add_global_log("BANANA", "fortress", msg)
            self.event_bus.publish_nowait(Event(type=EventType.BANANA_MODE, data={"active": True, "message": msg}))
        else:
            msg = "🍌 BANANA MODE DISENGAGED. Workers resumed to normal operations."
            self.state.add_global_log("BANANA", "fortress", msg)
            self.event_bus.publish_nowait(Event(type=EventType.BANANA_MODE, data={"active": False, "message": msg}))

        return self.state.banana_mode

    def pause_minion(self, minion_id: str) -> bool:
        minion = self.state.minions.get(minion_id)
        if minion:
            minion.status = MinionStatus.PAUSED
            minion.current_task = "PAUSED by Fortress Command"
            self.state.add_global_log("WARN", f"minion-{minion_id}", "Worker paused by operator.")
            return True
        return False

    def resume_minion(self, minion_id: str) -> bool:
        minion = self.state.minions.get(minion_id)
        if minion:
            minion.status = MinionStatus.RUNNING
            minion.last_heartbeat = time.time()
            minion.current_task = "Resumed active task processing"
            self.state.add_global_log("INFO", f"minion-{minion_id}", "Worker resumed.")
            return True
        return False

    def trigger_test_error(self, minion_id: str) -> bool:
        """Injected test error to demonstrate Watchdog auto-healing."""
        minion = self.state.minions.get(minion_id)
        if minion:
            minion.status = MinionStatus.ERROR
            minion.error_count += 1
            err_msg = f"SIMULATED_EXCEPTION: Fatal unhandled memory fault in task pipeline of {minion.name}"
            minion.add_log("FATAL", err_msg)
            self.state.add_global_log("FATAL", f"minion-{minion_id}", err_msg)
            self.event_bus.publish_nowait(
                Event(
                    type=EventType.ERROR,
                    data={"source": f"minion-{minion_id}", "level": "FATAL", "message": err_msg, "minion_id": minion_id},
                )
            )
            return True
        return False

    def switch_model(self, minion_id: str, new_model: str) -> bool:
        minion = self.state.minions.get(minion_id)
        if minion:
            minion.model = new_model
            msg = f"Model switched to {new_model}"
            minion.add_log("INFO", msg)
            self.state.add_global_log("INFO", f"minion-{minion_id}", msg)
            return True
        return False

    def spawn_minion(self, name: str, model: str = "qwen-2.5-coder") -> str:
        next_id = f"{len(self.state.minions) + 1:02d}"
        minion = MinionState(
            id=next_id,
            name=name,
            model=model,
            status=MinionStatus.RUNNING,
            current_task="Spawned and awaiting tasks",
        )
        minion.add_log("INFO", "Worker spawned successfully.")
        self.state.minions[next_id] = minion
        self.state.add_global_log("INFO", "fortress", f"Spawned new minion [{next_id}: {name}]")
        return next_id
