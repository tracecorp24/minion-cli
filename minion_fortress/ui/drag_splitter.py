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
        target_id: Optional ID of the widget before this splitter to resize.
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
        self.prev_target = None
        self.next_target = None
        self.initial_prev_size: int = 0
        self.initial_next_size: int = 0

    def _get_adjacent_pair(self):
        """Returns the (prev_widget, next_widget) adjacent to this splitter."""
        if not self.parent or not self.parent.children:
            return None, None

        siblings = list(self.parent.children)
        try:
            idx = siblings.index(self)
        except ValueError:
            return None, None

        prev_w = None
        for i in range(idx - 1, -1, -1):
            if not isinstance(siblings[i], DragSplitter):
                prev_w = siblings[i]
                break

        next_w = None
        for i in range(idx + 1, len(siblings)):
            if not isinstance(siblings[i], DragSplitter):
                next_w = siblings[i]
                break

        return prev_w, next_w

    def _get_target_widget(self):
        """Backwards-compatible helper returning the previous widget."""
        prev_w, _ = self._get_adjacent_pair()
        return prev_w

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1:  # Left mouse button for drag
            prev_w, next_w = self._get_adjacent_pair()
            if not prev_w:
                return

            self.dragging = True
            self.start_x = event.screen_x
            self.start_y = event.screen_y
            self.prev_target = prev_w
            self.next_target = next_w

            # Freeze sibling non-splitter widgets to outer_size to prevent flex-box jumping
            if self.parent:
                for child in self.parent.children:
                    if not isinstance(child, DragSplitter):
                        if self.direction == "horizontal":
                            child.styles.width = child.outer_size.width or child.size.width
                        else:
                            child.styles.height = child.outer_size.height or child.size.height

            if self.direction == "horizontal":
                self.initial_prev_size = prev_w.outer_size.width or prev_w.size.width or 40
                self.initial_next_size = (next_w.outer_size.width or next_w.size.width or 40) if next_w else 0
            else:
                self.initial_prev_size = prev_w.outer_size.height or prev_w.size.height or 15
                self.initial_next_size = (next_w.outer_size.height or next_w.size.height or 15) if next_w else 0

            self.add_class("active-drag")
            self.capture_mouse()
            event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self.dragging or not self.prev_target:
            return

        if self.direction == "horizontal":
            total_dx = event.screen_x - self.start_x
            if self.next_target:
                combined = self.initial_prev_size + self.initial_next_size
                min_w = 12
                if combined >= 2 * min_w:
                    new_prev = max(min_w, min(combined - min_w, self.initial_prev_size + total_dx))
                    new_next = combined - new_prev
                    self.prev_target.styles.width = new_prev
                    self.next_target.styles.width = new_next
            else:
                new_prev = max(12, self.initial_prev_size + total_dx)
                self.prev_target.styles.width = new_prev
        else:
            total_dy = event.screen_y - self.start_y
            if self.next_target:
                combined = self.initial_prev_size + self.initial_next_size
                min_h = 5
                if combined >= 2 * min_h:
                    new_prev = max(min_h, min(combined - min_h, self.initial_prev_size + total_dy))
                    new_next = combined - new_prev
                    self.prev_target.styles.height = new_prev
                    self.next_target.styles.height = new_next
            else:
                new_prev = max(5, self.initial_prev_size + total_dy)
                self.prev_target.styles.height = new_prev

        event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self.dragging:
            self.dragging = False
            self.prev_target = None
            self.next_target = None
            self.remove_class("active-drag")
            self.release_mouse()
            event.stop()

    def on_mouse_capture_out(self) -> None:
        self.dragging = False
        self.prev_target = None
        self.next_target = None
        self.remove_class("active-drag")
