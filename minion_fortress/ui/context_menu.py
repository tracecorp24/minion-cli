"""
Right-Click Context Menu & CLI Selector Modals for Minion Fortress.
Provides intuitive dialogs for splitting, detaching, switching CLIs, and closing tiles.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding


class TileContextMenu(ModalScreen[Dict[str, Any]]):
    """Context menu opened via right-click or header button on a CLI tile."""

    DEFAULT_CSS = """
    TileContextMenu {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #menu-container {
        width: 48;
        height: auto;
        border: heavy #FFE135;
        background: #181818;
        padding: 1 2;
    }
    .ctx-header {
        text-align: center;
        text-style: bold;
        color: #FFE135;
        background: #252525;
        padding: 1;
        margin-bottom: 1;
    }
    .ctx-btn {
        width: 100%;
        margin-bottom: 1;
        background: #2A2A2A;
        color: #FFFFFF;
        border: none;
        height: 3;
    }
    .ctx-btn:hover {
        background: #FFE135;
        color: #000000;
        text-style: bold;
    }
    .ctx-btn-danger {
        color: #FF5555;
    }
    .ctx-btn-danger:hover {
        background: #FF4444;
        color: #FFFFFF;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "İptal", priority=True),
    ]

    def __init__(self, tile_id: str, current_cli: str) -> None:
        super().__init__()
        self.tile_id = tile_id
        self.current_cli = current_cli

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            yield Static(f"⚡ PENCERE İŞLEMLERİ: {self.current_cli.upper()}", classes="ctx-header")
            yield Button("⬌ Dikey Böl (Sağa Yeni CLI Ekle)", id="btn-split-v", classes="ctx-btn")
            yield Button("⬍ Yatay Böl (Aşağı Yeni CLI Ekle)", id="btn-split-h", classes="ctx-btn")
            yield Button("🗗 Birleşik Düzenden Ayır (Ayrı Windows Penceresi)", id="btn-detach", classes="ctx-btn")
            yield Button("🔄 CLI Türünü Değiştir...", id="btn-switch", classes="ctx-btn")
            yield Button("✖ Bu Pencereyi Kapat", id="btn-close", classes="ctx-btn ctx-btn-danger")
            yield Button("❌ Vazgeç", id="btn-cancel", classes="ctx-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        actions = {
            "btn-split-v": {"action": "split_v", "tile_id": self.tile_id},
            "btn-split-h": {"action": "split_h", "tile_id": self.tile_id},
            "btn-detach": {"action": "detach", "tile_id": self.tile_id, "cli_type": self.current_cli},
            "btn-switch": {"action": "open_cli_selector", "tile_id": self.tile_id},
            "btn-close": {"action": "close", "tile_id": self.tile_id},
            "btn-cancel": {"action": "cancel", "tile_id": self.tile_id},
        }
        self.dismiss(actions.get(btn_id, {"action": "cancel", "tile_id": self.tile_id}))

    def action_cancel(self) -> None:
        self.dismiss({"action": "cancel", "tile_id": self.tile_id})


class CliSelectorModal(ModalScreen[Optional[str]]):
    """Modal dialog allowing the operator to assign any CLI or tool to a pane."""

    DEFAULT_CSS = """
    CliSelectorModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #selector-container {
        width: 58;
        height: auto;
        border: heavy #00FF7F;
        background: #141414;
        padding: 1 2;
    }
    .sel-header {
        text-align: center;
        text-style: bold;
        color: #00FF7F;
        background: #1F1F1F;
        padding: 1;
        margin-bottom: 1;
    }
    .sel-btn {
        width: 100%;
        margin-bottom: 1;
        background: #222222;
        color: #FFFFFF;
        border: none;
        height: 3;
    }
    .sel-btn:hover {
        background: #00FF7F;
        color: #000000;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "İptal", priority=True),
    ]

    CLI_CHOICES = [
        ("minion-01", "🤖 Minion-01 (ast-parser • qwen-2.5-coder)"),
        ("minion-02", "🤖 Minion-02 (net-mon • glm-4-flash)"),
        ("minion-03", "🤖 Minion-03 (quant • deepseek-r1)"),
        ("minion-04", "🤖 Minion-04 (doc-ext • qwen-2.5-coder)"),
        ("minion-05", "🤖 Minion-05 (code-synth • qwen-2.5-coder)"),
        ("shell", "💻 İnteraktif Shell CLI (Sistem & Python Konsolu)"),
        ("error", "🚨 Watchdog Hata & Otomatik İyileştirme Monitörü"),
        ("sniper", "🎯 Log Sniper (Canlı Regex Filtreleme)"),
        ("plugins", "🧩 Eklenti & Araç Mağazası (Plugin Hub)"),
    ]

    def __init__(self, tile_id: str, current_cli: str) -> None:
        super().__init__()
        self.tile_id = tile_id
        self.current_cli = current_cli

    def compose(self) -> ComposeResult:
        with Vertical(id="selector-container"):
            yield Static("🔄 BU PENCERE İÇİN YENİ CLI SEÇİN", classes="sel-header")
            for cli_id, label in self.CLI_CHOICES:
                suffix = " [MEVCUT]" if cli_id == self.current_cli else ""
                yield Button(f"{label}{suffix}", id=f"cli-opt-{cli_id}", classes="sel-btn")
            yield Button("❌ İptal", id="cli-opt-cancel", classes="sel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "cli-opt-cancel":
            self.dismiss(None)
            return

        cli_key = btn_id.replace("cli-opt-", "")
        self.dismiss(cli_key)

    def action_cancel(self) -> None:
        self.dismiss(None)
