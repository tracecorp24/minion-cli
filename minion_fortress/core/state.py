"""
Core State and RingBuffer management for Minion Fortress v3.0.
Provides zero-lag in-memory ring buffers, time-travel history tracking,
and snapshot export facilities.
"""

from __future__ import annotations
import time
import json
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar("T")


class RingBuffer(Generic[T]):
    """Thread-safe fixed-size ring buffer with time-travel rewind support."""

    def __init__(self, maxlen: int = 500) -> None:
        self.maxlen = maxlen
        self._buffer: deque[T] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def append(self, item: T) -> None:
        with self._lock:
            self._buffer.append(item)

    def extend(self, items: List[T]) -> None:
        with self._lock:
            self._buffer.extend(items)

    def get_all(self) -> List[T]:
        with self._lock:
            return list(self._buffer)

    def get_recent(self, n: int = 50) -> List[T]:
        with self._lock:
            items = list(self._buffer)
            return items[-n:] if n <= len(items) else items

    def replay(self, steps_back: int = 50) -> List[T]:
        """
        Rewind capability for Time Travel (Feature 6).
        Returns a slice of history up to steps_back steps ago.
        """
        with self._lock:
            items = list(self._buffer)
            if not items:
                return []
            if steps_back >= len(items):
                return items
            return items[-steps_back:]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


class MinionStatus(str, Enum):
    RUNNING = "RUNNING"
    BUSY = "BUSY"
    IDLE = "IDLE"
    ERROR = "ERROR"
    PAUSED = "PAUSED"
    HEALING = "HEALING"


@dataclass
class LogEntry:
    timestamp: str
    level: str  # INFO, WARN, ERROR, FATAL, HEAL, BANANA
    source: str
    message: str

    def to_formatted_str(self) -> str:
        color = {
            "INFO": "cyan",
            "WARN": "yellow",
            "ERROR": "red",
            "FATAL": "bold red",
            "HEAL": "bold green",
            "BANANA": "bold #FFE135",
        }.get(self.level.upper(), "white")
        return f"[{self.timestamp}] [{self.level}] ({self.source}) {self.message}"


@dataclass
class MinionState:
    id: str
    name: str
    status: MinionStatus = MinionStatus.RUNNING
    cpu: float = 0.0
    memory_mb: float = 0.0
    progress: int = 0
    current_task: str = "Initializing worker..."
    model: str = "qwen-2.5-coder"
    last_heartbeat: float = field(default_factory=time.time)
    error_count: int = 0
    logs: RingBuffer[LogEntry] = field(default_factory=lambda: RingBuffer[LogEntry](maxlen=500))
    history_snapshots: RingBuffer[Dict[str, Any]] = field(
        default_factory=lambda: RingBuffer[Dict[str, Any]](maxlen=100)
    )

    def record_snapshot(self) -> None:
        """Saves a point-in-time snapshot for time travel replay."""
        snap = {
            "timestamp": time.strftime("%H:%M:%S"),
            "progress": self.progress,
            "status": self.status.value,
            "current_task": self.current_task,
            "cpu": self.cpu,
        }
        self.history_snapshots.append(snap)

    def add_log(self, level: str, message: str) -> LogEntry:
        now_str = time.strftime("%H:%M:%S")
        entry = LogEntry(timestamp=now_str, level=level, source=f"minion-{self.id}", message=message)
        self.logs.append(entry)
        return entry


class FortressState:
    """Global cluster state and metrics tracker."""

    def __init__(self) -> None:
        self.start_time: float = time.time()
        self.total_tasks: int = 1445
        self.completed_tasks: int = 1420
        self.failed_tasks: int = 5
        self.token_cost: float = 0.042
        self.banana_mode: bool = False
        self.minions: Dict[str, MinionState] = {}
        self.global_logs: RingBuffer[LogEntry] = RingBuffer[LogEntry](maxlen=2000)
        self.error_logs: RingBuffer[LogEntry] = RingBuffer[LogEntry](maxlen=1000)
        self.plugins: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get_active_minion_count(self) -> int:
        with self._lock:
            return sum(1 for m in self.minions.values() if m.status in (MinionStatus.RUNNING, MinionStatus.BUSY))

    def get_total_minion_count(self) -> int:
        with self._lock:
            return len(self.minions)

    def add_global_log(self, level: str, source: str, message: str) -> LogEntry:
        now_str = time.strftime("%H:%M:%S")
        entry = LogEntry(timestamp=now_str, level=level, source=source, message=message)
        self.global_logs.append(entry)
        if level.upper() in ("ERROR", "FATAL", "WARN", "HEAL"):
            self.error_logs.append(entry)
        return entry

    def export_snapshot(self, export_dir: Path | str) -> tuple[Path, Path]:
        """
        Exports current fortress state, telemetry, and log buffers to both
        Markdown (.md) and JSON (.json) format (Feature 9).
        """
        path_obj = Path(export_dir)
        path_obj.mkdir(parents=True, exist_ok=True)
        ts_slug = time.strftime("%Y%m%d_%H%M%S")
        ts_pretty = time.strftime("%Y-%m-%d %H:%M:%S")

        md_path = path_obj / f"fortress_session_{ts_slug}.md"
        json_path = path_obj / f"fortress_session_{ts_slug}.json"

        # Prepare JSON data
        with self._lock:
            minion_dump = {}
            for mid, m in self.minions.items():
                minion_dump[mid] = {
                    "id": m.id,
                    "name": m.name,
                    "status": m.status.value,
                    "model": m.model,
                    "progress": m.progress,
                    "cpu": m.cpu,
                    "memory_mb": m.memory_mb,
                    "current_task": m.current_task,
                    "error_count": m.error_count,
                    "recent_logs": [asdict(e) for e in m.logs.get_recent(20)],
                }

            plugin_dump = {
                k: {"name": p.name, "version": getattr(p, "version", "1.0"), "active": getattr(p, "is_active", True)}
                for k, p in self.plugins.items()
            }

            state_data = {
                "timestamp": ts_pretty,
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "banana_mode": self.banana_mode,
                "telemetry": {
                    "total_tasks": self.total_tasks,
                    "completed_tasks": self.completed_tasks,
                    "failed_tasks": self.failed_tasks,
                    "completion_rate_pct": round((self.completed_tasks / max(1, self.total_tasks)) * 100, 2),
                    "token_cost_usd": round(self.token_cost, 4),
                    "active_minions": self.get_active_minion_count(),
                    "total_minions": self.get_total_minion_count(),
                },
                "minions": minion_dump,
                "plugins": plugin_dump,
                "recent_errors": [asdict(e) for e in self.error_logs.get_recent(50)],
                "recent_logs": [asdict(e) for e in self.global_logs.get_recent(50)],
            }

        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(state_data, jf, indent=2, ensure_ascii=False)

        # Build clean Markdown report
        md_content = f"""# 🍌 MINION-FORTRESS (KOVAN-X) Session Snapshot
Generated: `{ts_pretty}` | Uptime: `{state_data['uptime_seconds']}s` | Banana Mode: `{'ACTIVE' if self.banana_mode else 'NORMAL'}`

---

## 📊 1. Cluster Telemetry
| Metric | Value |
|---|---|
| Total Tasks | {self.total_tasks} |
| Completed Tasks | {self.completed_tasks} ({state_data['telemetry']['completion_rate_pct']}%) |
| Failed Tasks | {self.failed_tasks} |
| Token Cost ($) | ${self.token_cost:.4f} |
| Active Minions | {state_data['telemetry']['active_minions']} / {state_data['telemetry']['total_minions']} |

---

## 🤖 2. Minion Roster
| ID | Name | Model | Status | Progress | CPU % | Memory | Current Task | Errors |
|---|---|---|---|---|---|---|---|---|
"""
        for mid, m in minion_dump.items():
            md_content += f"| {m['id']} | `{m['name']}` | `{m['model']}` | **{m['status']}** | {m['progress']}% | {m['cpu']}% | {m['memory_mb']} MB | {m['current_task']} | {m['error_count']} |\n"

        md_content += """
---

## 🔌 3. Active Plugins & Tools
| Plugin | Version | Status |
|---|---|---|
"""
        for p_name, p_info in plugin_dump.items():
            st = "Active 🟢" if p_info.get("active") else "Paused ⏸️"
            md_content += f"| `{p_name}` | {p_info.get('version')} | {st} |\n"

        md_content += """
---

## 🚨 4. Recent Error & Health Events (Last 20)
```text
"""
        recent_errs = self.error_logs.get_recent(20)
        if recent_errs:
            for err in recent_errs:
                md_content += f"[{err.timestamp}] [{err.level}] ({err.source}) {err.message}\n"
        else:
            md_content += "No critical errors recorded. System healthy.\n"

        md_content += """```

---

## 📜 5. Global Log Stream Sample (Last 25)
```text
"""
        for log in self.global_logs.get_recent(25):
            md_content += f"[{log.timestamp}] [{log.level}] ({log.source}) {log.message}\n"

        md_content += "```\n"

        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write(md_content)

        return md_path, json_path
