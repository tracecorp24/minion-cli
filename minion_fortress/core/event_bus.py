"""
Event Bus and Async Pub/Sub with Zero-Lag IPC support.
Enables detached nodes and internal daemon workers to broadcast
logs, heartbeats, and status changes seamlessly.
"""

from __future__ import annotations
import asyncio
import inspect
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Set

logger = logging.getLogger("EventBus")


class EventType(str, Enum):
    LOG = "LOG"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"
    STATUS_CHANGE = "STATUS_CHANGE"
    TELEMETRY = "TELEMETRY"
    BANANA_MODE = "BANANA_MODE"
    REPLAY_REQUEST = "REPLAY_REQUEST"
    PLUGIN_CHANGE = "PLUGIN_CHANGE"
    COMMAND = "COMMAND"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Zero-lag async Pub/Sub event bus with bidirectional IPC socket capability."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, Set[Callable[[Event], Any]]] = {et: set() for et in EventType}
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=10000)
        self._running: bool = False
        self._worker_task: asyncio.Task | None = None
        self._ipc_server: asyncio.Server | None = None
        self._ipc_clients: Set[asyncio.StreamWriter] = set()

    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """Subscribe a sync or async callback to an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].add(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish_nowait(self, event: Event) -> None:
        """Non-blocking zero-lag enqueue. If queue is full, discards oldest or ignores without blocking."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop earliest to guarantee UI zero lag
            try:
                _ = self._queue.get_nowait()
                self._queue.put_nowait(event)
            except Exception:
                pass

    async def publish(self, event: Event) -> None:
        """Async publish."""
        self.publish_nowait(event)

    async def start(
        self,
        host: str = "127.0.0.1",
        port: int = 42010,
        unix_socket_path: str = "/tmp/minion_fortress.sock",
    ) -> None:
        """Starts the event distribution loop and the local IPC server (Unix Domain Socket / TCP fallback)."""
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())

        # 1. Attempt Unix Domain Socket where supported by OS
        if hasattr(asyncio, "start_unix_server") and os.name != "nt":
            try:
                if os.path.exists(unix_socket_path):
                    os.remove(unix_socket_path)
                self._ipc_server = await asyncio.start_unix_server(self._handle_ipc_client, path=unix_socket_path)
                return
            except Exception:
                pass

        # 2. Loopback TCP IPC Server (Windows & network fallback)
        try:
            self._ipc_server = await asyncio.start_server(self._handle_ipc_client, host, port)
        except Exception as e:
            logger.warning(f"Failed to start TCP IPC server on {host}:{port}: {e}")
            self._ipc_server = None

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
        for client in list(self._ipc_clients):
            try:
                client.close()
            except Exception:
                pass
        self._ipc_clients.clear()
        if self._ipc_server:
            self._ipc_server.close()
            await self._ipc_server.wait_closed()

    async def _process_queue(self) -> None:
        while self._running:
            try:
                event = await self._queue.get()
                handlers = self._subscribers.get(event.type, set())
                for handler in list(handlers):
                    try:
                        if inspect.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event))
                        else:
                            handler(event)
                    except Exception as ex:
                        logger.error(f"Error executing event handler {handler}: {ex}")

                # Broadcast to external detached window nodes via IPC sockets
                if self._ipc_clients:
                    payload = json.dumps(
                        {
                            "type": event.type.value if hasattr(event.type, "value") else str(event.type),
                            "data": event.data,
                            "timestamp": event.timestamp,
                        }
                    ).encode("utf-8") + b"\n"

                    async def _broadcast_to_client(w: asyncio.StreamWriter, p: bytes) -> None:
                        try:
                            w.write(p)
                            await asyncio.wait_for(w.drain(), timeout=0.25)
                        except Exception:
                            self._ipc_clients.discard(w)

                    for client in list(self._ipc_clients):
                        asyncio.create_task(_broadcast_to_client(client, payload))

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event bus loop error: {e}")

    async def _handle_ipc_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles external IPC connections, reads inbound commands, and keeps stream open for broadcasts."""
        self._ipc_clients.add(writer)
        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                try:
                    payload = json.loads(line.decode("utf-8").strip())
                    ev_type = EventType(payload.get("type", "LOG"))
                    ev = Event(type=ev_type, data=payload.get("data", {}))
                    self.publish_nowait(ev)
                except Exception:
                    pass
        finally:
            self._ipc_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
