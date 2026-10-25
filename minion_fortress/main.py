"""
Minion Fortress v3.0 CLI Entrypoint.
Supports interactive TUI mode, headless daemon mode, and CLI snapshot export.
"""

from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus
from minion_fortress.core.daemon import MinionDaemon
from minion_fortress.plugins.manager import PluginManager
from minion_fortress.ui.app import MinionFortressApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="🍌 MINION-FORTRESS (KOVAN-X) v3.0: High-Performance Multi-Agent Mission Control"
    )
    parser.add_argument("--daemon", action="store_true", help="Run background daemon without TUI")
    parser.add_argument("--export", action="store_true", help="Generate instantaneous system snapshot report and exit")
    parser.add_argument("--version", action="version", version="Minion Fortress v3.0.0")
    return parser.parse_args()


def run_app() -> None:
    args = parse_args()

    state = FortressState()
    event_bus = EventBus()
    plugin_mgr = PluginManager()
    state.plugins = plugin_mgr.get_all()
    daemon = MinionDaemon(state, event_bus, plugin_mgr)

    if args.export:
        reports_dir = Path("reports")
        md_file, json_file = state.export_snapshot(reports_dir)
        print(f"Snapshot exported successfully:")
        print(f"  Markdown: {md_file.resolve()}")
        print(f"  JSON:     {json_file.resolve()}")
        sys.exit(0)

    if args.daemon:
        print("Starting Minion Fortress Daemon in headless mode (Press Ctrl+C to stop)...")

        async def run_daemon_headless():
            await event_bus.start()
            await daemon.start()
            try:
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                await daemon.stop()
                await event_bus.stop()

        try:
            asyncio.run(run_daemon_headless())
        except KeyboardInterrupt:
            print("\nDaemon terminated cleanly.")
        sys.exit(0)

    # Interactive TUI Mode
    app = MinionFortressApp(state=state, event_bus=event_bus, daemon=daemon, plugin_manager=plugin_mgr)
    app.run()


if __name__ == "__main__":
    run_app()
