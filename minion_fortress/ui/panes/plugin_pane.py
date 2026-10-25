"""
Feature 7: Plugin Hub & Tool Store Pane (Özellik 7: 🔌 Eklenti ve Araç Mağazası)
Allows hot-reloading, monitoring, and live activation/pausing of external minion tools.
"""

from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual import on

from minion_fortress.core.state import FortressState
from minion_fortress.core.event_bus import EventBus, Event, EventType
from minion_fortress.plugins.manager import PluginManager


class PluginPane(Vertical):
    """Interactive Hub for managing external LLM tools and integrations."""

    def __init__(self, state: FortressState, event_bus: EventBus, plugin_manager: PluginManager) -> None:
        super().__init__(classes="pane-container")
        self.state = state
        self.event_bus = event_bus
        self.plugin_manager = plugin_manager

    def compose(self) -> ComposeResult:
        yield Static("🔌 PLUGIN HUB & TOOL STORE (Hot-Reload)", classes="pane-title plugin-title")
        with Horizontal(classes="action-bar"):
            yield Static("Installed Plugins: ", id="plugin-header-label")
            yield Button("🔄 Rescan", id="btn-rescan-plugins")

        yield Vertical(id="plugin-cards-container")

    def on_mount(self) -> None:
        self.event_bus.subscribe(EventType.PLUGIN_CHANGE, self._on_plugin_event)
        self.refresh_plugins_list()

    def refresh_plugins_list(self) -> None:
        """Renders list of loaded tools with toggle controls."""
        try:
            container = self.query_one("#plugin-cards-container", Vertical)
            container.remove_children()

            plugins = self.plugin_manager.get_all()
            for name, plugin in plugins.items():
                is_active = getattr(plugin, "is_active", True)
                version = getattr(plugin, "version", "1.0")
                desc = getattr(plugin, "description", "")

                status_badge = "[bold green][x] Active[/bold green]" if is_active else "[bold yellow][ ] Paused[/bold yellow]"
                card_text = f"{status_badge} [bold white]{name}[/bold white] (v{version})\n   [dim]{desc}[/dim]"

                row = Horizontal(classes="action-bar")
                row.mount(Static(card_text, classes="plugin-info-static"))

                btn_label = "Pause" if is_active else "Activate"
                btn_cls = "paused-btn" if is_active else "active-btn"
                btn_id = f"btn-toggle-{name.replace(' ', '-').replace('.', '_')}"
                btn = Button(btn_label, id=btn_id, classes=btn_cls)
                row.mount(btn)

                container.mount(row)
        except Exception:
            pass

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-rescan-plugins":
            self.plugin_manager.load_all()
            self.refresh_plugins_list()
            self.state.add_global_log("INFO", "plugin-mgr", "Hot-reloaded all plugins from disk.")
            return

        if btn_id and btn_id.startswith("btn-toggle-"):
            clean_name = btn_id.replace("btn-toggle-", "")
            # Find matching plugin name
            for name in list(self.plugin_manager.get_all().keys()):
                target = name.replace(" ", "-").replace(".", "_")
                if target == clean_name:
                    new_status = self.plugin_manager.toggle_plugin(name)
                    st_str = "ACTIVE" if new_status else "PAUSED"
                    self.state.add_global_log("INFO", "plugin-mgr", f"Plugin [{name}] switched to {st_str}")
                    self.refresh_plugins_list()
                    break

    def _on_plugin_event(self, event: Event) -> None:
        self.app.call_from_thread(self.refresh_plugins_list)
