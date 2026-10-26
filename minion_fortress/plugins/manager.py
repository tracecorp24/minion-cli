"""
Plugin Manager for Minion Fortress (Feature 7: Plugin Hub / Tool Store).
Scans plugins/ directory, manages hot-reloading, and handles state toggles with event bus notifications.
"""

from __future__ import annotations
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, Optional


class PluginManager:
    def __init__(self, plugins_dir: Path | str | None = None, event_bus: Any = None) -> None:
        if plugins_dir is None:
            self.plugins_dir = Path(__file__).parent
        else:
            self.plugins_dir = Path(plugins_dir)
        self.event_bus = event_bus
        self.plugins: Dict[str, Any] = {}
        self.load_all()

    def set_event_bus(self, event_bus: Any) -> None:
        self.event_bus = event_bus

    def load_all(self) -> Dict[str, Any]:
        """Discovers and instantiates all plugin modules in the plugins directory."""
        from minion_fortress.plugins.docling_tool import DoclingPlugin
        from minion_fortress.plugins.pgvector_tool import PgVectorPlugin
        from minion_fortress.plugins.telegram_tool import TelegramPlugin
        from minion_fortress.plugins.openrouter_tool import OpenRouterPlugin

        # Standard builtin plugins
        self.plugins["Docling-v2"] = DoclingPlugin()
        self.plugins["pgvector-sync"] = PgVectorPlugin()
        self.plugins["Telegram-Bot"] = TelegramPlugin()
        self.plugins["OpenRouter-API"] = OpenRouterPlugin()

        # Dynamic scanner for any extra user plugins dropped into plugins/
        for pfile in self.plugins_dir.glob("*.py"):
            if pfile.stem.startswith("__") or pfile.stem in ("manager", "docling_tool", "pgvector_tool", "telegram_tool", "openrouter_tool"):
                continue
            try:
                mod_name = f"minion_fortress.plugins.{pfile.stem}"
                mod = importlib.import_module(mod_name)
                importlib.reload(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if inspect.isclass(attr) and (attr_name.endswith("Plugin") or attr_name.endswith("Tool")):
                        instance = attr()
                        plugin_name = getattr(instance, "name", attr_name)
                        self.plugins[plugin_name] = instance
            except Exception:
                pass

        return self.plugins

    def toggle_plugin(self, name: str) -> bool:
        """Toggles active/paused state of a plugin with smart fuzzy/partial matching and broadcasts change."""
        # 1. Exact match
        plugin = self.plugins.get(name)

        # 2. Case-insensitive / normalized search fallback
        if not plugin:
            clean_search = name.lower().replace("-", "").replace(" ", "").replace("_", "")
            for p_name, p_inst in self.plugins.items():
                clean_target = p_name.lower().replace("-", "").replace(" ", "").replace("_", "")
                if clean_search in clean_target or clean_target in clean_search:
                    plugin = p_inst
                    name = p_name
                    break

        if plugin and hasattr(plugin, "toggle"):
            new_state = plugin.toggle()
            if self.event_bus:
                try:
                    from minion_fortress.core.event_bus import Event, EventType
                    self.event_bus.publish_nowait(
                        Event(
                            type=EventType.PLUGIN_CHANGE,
                            data={"name": name, "is_active": new_state},
                        )
                    )
                except Exception:
                    pass
            return new_state
        return False

    def get_plugin(self, name: str) -> Any:
        plugin = self.plugins.get(name)
        if not plugin:
            clean_search = name.lower().replace("-", "").replace(" ", "").replace("_", "")
            for p_name, p_inst in self.plugins.items():
                clean_target = p_name.lower().replace("-", "").replace(" ", "").replace("_", "")
                if clean_search in clean_target or clean_target in clean_search:
                    return p_inst
        return plugin

    def get_all(self) -> Dict[str, Any]:
        return self.plugins
