"""
Visual theme, color palettes, CSS definitions, and ASCII art
for Minion Fortress v3.0.
"""

from __future__ import annotations

# Minion Palette
BANANA_YELLOW = "#FFE135"
BANANA_GOLD = "#FFD700"
DARK_BG = "#121212"
PANEL_BG = "#1A1A1A"
BORDER_YELLOW = "#FFE135"
BORDER_GRAY = "#333333"
ERROR_RED = "#FF4444"
WARN_ORANGE = "#FFA500"
HEAL_GREEN = "#00FF7F"
INFO_CYAN = "#00E5FF"
TEXT_WHITE = "#EDEDED"
TEXT_MUTED = "#888888"

# ASCII Art Minion
MINION_ASCII_ACTIVE = """
  (o) > Task: {task}
 |█| > [PROGRESS] [{bar}] {progress}%
  / \\ > Status: {status} | CPU: {cpu}% | RAM: {mem}MB
"""

MINION_ASCII_BANANA = """
  (♥_♥) 🍌 BANANA! BANANA! BANANA! 🍌
   |█|  > EMERGENCY PANIC MODE ENGAGED <
   / \\  > ALL PROCESSORS SAFE-LOCKED <
"""

FORTRESS_CSS = f"""
Screen {{
    background: {DARK_BG};
    color: {TEXT_WHITE};
}}

Header {{
    dock: top;
    height: 1;
    background: #181818;
    color: {BANANA_YELLOW};
    text-style: bold;
}}

Footer {{
    dock: bottom;
    height: 1;
    background: #181818;
    color: {BANANA_YELLOW};
}}

#app-grid {{
    layout: horizontal;
    height: 1fr;
}}

#left-sidebar {{
    width: 38;
    border-right: heavy {BORDER_YELLOW};
    background: {PANEL_BG};
    padding: 0 1;
}}

#right-canvas {{
    width: 1fr;
    layout: vertical;
    padding: 0;
}}

.grid-row {{
    height: 1fr;
    layout: horizontal;
}}

.pane-container {{
    width: 1fr;
    height: 100%;
    border: heavy {BORDER_YELLOW};
    background: {PANEL_BG};
    margin: 0;
    padding: 0;
}}

.pane-title {{
    height: 1;
    background: {BANANA_YELLOW};
    color: #000000;
    text-style: bold;
    padding-left: 1;
}}

.error-title {{
    background: {ERROR_RED};
    color: #FFFFFF;
}}

.sniper-title {{
    background: {BANANA_GOLD};
    color: #000000;
}}

.plugin-title {{
    background: #9D00FF;
    color: #FFFFFF;
}}

.log-stream {{
    height: 1fr;
    background: #0D0D0D;
    color: #C0C0C0;
    padding: 0 1;
    scrollbar-color: {BANANA_YELLOW} #222222;
}}

#repl-container {{
    dock: bottom;
    height: 3;
    border-top: heavy {BORDER_YELLOW};
    background: #181818;
    padding: 0 1;
}}

#repl-input {{
    background: #0F0F0F;
    border: tall {BANANA_YELLOW};
    color: {BANANA_YELLOW};
}}

.telemetry-card {{
    background: #202020;
    border: solid {BORDER_GRAY};
    padding: 1;
    margin-bottom: 1;
}}

.section-header {{
    text-style: bold;
    color: {BANANA_YELLOW};
    margin-top: 1;
    margin-bottom: 0;
}}

.minion-avatar-box {{
    background: #141414;
    border: solid #444444;
    color: {BANANA_YELLOW};
    padding: 0 1;
    margin-bottom: 1;
}}

.action-bar {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    background: #181818;
    align: center middle;
}}

Button {{
    background: #2A2A2A;
    color: {BANANA_YELLOW};
    border: solid {BORDER_YELLOW};
    min-width: 12;
    margin-right: 1;
}}

Button:hover {{
    background: {BANANA_YELLOW};
    color: #000000;
}}

Button.active-btn {{
    background: {HEAL_GREEN};
    color: #000000;
}}

Button.paused-btn {{
    background: #444444;
    color: #AAAAAA;
}}

/* Dynamic Workspace and Tiling Styles */
#workspace-canvas {{
    width: 100%;
    height: 1fr;
    padding: 0;
    margin: 0;
}}

.split-col {{
    layout: horizontal;
    height: 100%;
    width: 100%;
}}

.split-row {{
    layout: vertical;
    height: 100%;
    width: 100%;
}}

#preset-toolbar {{
    height: 3;
    background: #141414;
    border-bottom: heavy {BORDER_YELLOW};
    padding: 0 1;
    layout: horizontal;
}}

.preset-label {{
    width: auto;
    color: {BANANA_YELLOW};
    text-style: bold;
    content-align: center middle;
    padding-right: 1;
}}

.preset-btn {{
    width: auto;
    min-width: 9;
    height: 1;
    margin: 0 1 0 0;
    background: #252525;
    color: #E0E0E0;
    border: none;
}}

.preset-btn:hover {{
    background: {BANANA_YELLOW};
    color: #000000;
    text-style: bold;
}}

.preset-btn-active {{
    background: {HEAL_GREEN};
    color: #000000;
    text-style: bold;
}}

CliTilePane {{
    border: heavy {BORDER_YELLOW};
    background: {PANEL_BG};
    height: 1fr;
    width: 1fr;
    margin: 0;
    padding: 0;
}}

CliTilePane:focus-within {{
    border: heavy {HEAL_GREEN};
}}

.tile-header-bar {{
    height: 1;
    background: #202020;
    padding: 0 1;
    layout: horizontal;
}}

.tile-title-text {{
    width: 1fr;
    color: {BANANA_YELLOW};
    text-style: bold;
}}

.tile-actions-strip {{
    width: auto;
    layout: horizontal;
}}

.tile-hdr-btn {{
    width: 4;
    min-width: 4;
    height: 1;
    padding: 0;
    margin: 0 0 0 1;
    background: #333333;
    color: #FFFFFF;
    border: none;
}}

.tile-hdr-btn:hover {{
    background: {BANANA_YELLOW};
    color: #000000;
    text-style: bold;
}}

.tile-hdr-btn-danger:hover {{
    background: {ERROR_RED};
    color: #FFFFFF;
}}

.tile-inner-container {{
    height: 1fr;
    width: 100%;
    padding: 0;
    margin: 0;
}}

.tile-input-container {{
    height: 3;
    background: #141414;
    border-top: solid #333333;
    padding: 0 1;
    layout: horizontal;
}}

.tile-prompt-tag {{
    width: auto;
    color: {HEAL_GREEN};
    text-style: bold;
    content-align: center middle;
    padding-right: 1;
}}

.tile-cli-input {{
    width: 1fr;
    background: #0A0A0A;
    border: tall {BORDER_YELLOW};
    color: #FFFFFF;
}}

DragSplitter {{
    background: #222222;
    color: {BANANA_YELLOW};
    text-align: center;
    content-align: center middle;
}}

DragSplitter:hover {{
    background: {HEAL_GREEN};
    color: #000000;
}}

DragSplitter.active-drag {{
    background: {BANANA_YELLOW};
    color: #000000;
}}

.splitter-h {{
    width: 1;
    height: 100%;
}}

.splitter-v {{
    height: 1;
    width: 100%;
}}

.shell-container {{
    height: 100%;
    width: 100%;
}}

.shell-title {{
    background: {INFO_CYAN};
    color: #000000;
}}
"""
