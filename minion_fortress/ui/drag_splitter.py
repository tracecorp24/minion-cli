"""
Interactive Mouse-Draggable Splitter / Divider for Dynamic Tiling Panes.
Supports horizontal (column width resize) and vertical (row height resize) dragging.
"""

from __future__ import annotations
from typing import Optional
from textual.widgets import Static
from textual import events


class DragSplitter(Static):
    """A mouse-draggable splitter divider that resizes adjacent panes."""

    DEFAULT_CSS = """
    DragSplitter {
        background: #2A2A2A;
        color: #FFE135;
        text-align: center;
        content-align: center middle;
    }
    DragSplitter:hover {
        background: #00FF7F;
        color: #000000;
    }
    DragSplitter.active-drag {
        background: #FFE135;
        color: #000000;
    }
    .splitter-h {
        width: 1;
        height: 100%;
    }
    .splitter-v {
        height: 1;
        width: 100%;
    }
    """

    def __init__(
        self,
        direction: str = "horizontal",
        target_id: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        direction: 'horizontal' (divides side-by-side columns, resizes width)
                   or 'vertical' (divides stacked rows, resizes height).
        target_id: ID of the widget before this splitter to resize.
                   If None, automatically targets the previous sibling.
        """
        self.direction = direction
        self.target_id = target_id
        symbol = "│" if direction == "horizontal" else "─"
        cls_list = ["splitter-h" if direction == "horizontal" else "splitter-v"]
        if classes:
            cls_list.append(classes)

        super().__init__(symbol, id=id, classes=" ".join(cls_list))
        self.dragging: bool = False
        self.start_x: int = 0
        self.start_y: int = 0

    def _get_target_widget(self):
        if self.target_id:
            try:
                return self.screen.query_one(f"#{self.target_id}")
            except Exception:
                pass

        # Fallback: previous sibling in parent
        if self.parent and self.parent.children:
            siblings = list(self.parent.children)
            try:
                idx = siblings.index(self)
                if idx > 0:
                    return siblings[idx - 1]
            except ValueError:
                pass
        return None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1:  # Left mouse button for drag
            self.dragging = True
            self.start_x = event.screen_x
            self.start_y = event.screen_y
            self.add_class("active-drag")
            self.capture_mouse()
            event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self.dragging:
            return

        target = self._get_target_widget()
        if not target:
            return

        if self.direction == "horizontal":
            dx = event.screen_x - self.start_x
            if abs(dx) >= 1:
                curr_w = target.size.width
                new_w = max(12, curr_w + dx)
                target.styles.width = new_w
                self.start_x = event.screen_x
        else:
            dy = event.screen_y - self.start_y
            if abs(dy) >= 1:
                curr_h = target.size.height
                new_h = max(4, curr_h + dy)
                target.styles.height = new_h
                self.start_y = event.screen_y

        event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self.dragging:
            self.dragging = False
            self.remove_class("active-drag")
            self.release_mouse()
            event.stop()

    def on_mouse_capture_out(self) -> None:
        self.dragging = False
        self.remove_class("active-drag")
