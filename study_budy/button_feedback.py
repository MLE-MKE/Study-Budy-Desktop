"""Reusable button click feedback for the PySide desktop UI."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton

CLICK_FEEDBACK_DELAY_MS = 400
CLICK_FEEDBACK_STYLESHEET = "background: white; color: black; border: 1px solid #303743;"


# ---- BUTTON CLICK FEEDBACK ----
# This section briefly changes my button colors so I can see that the click registered.
def run_with_click_feedback(
    button: QPushButton,
    action: Callable[[], None],
    delay_ms: int = CLICK_FEEDBACK_DELAY_MS,
) -> None:
    """Run a button action while briefly showing a high-contrast clicked state."""
    if not button.isEnabled():
        return

    original_stylesheet = button.property("_click_feedback_original_stylesheet")
    if original_stylesheet is None:
        original_stylesheet = button.styleSheet()
        button.setProperty("_click_feedback_original_stylesheet", original_stylesheet)

    token = time.monotonic_ns()
    button.setProperty("_click_feedback_token", token)
    button.setStyleSheet(CLICK_FEEDBACK_STYLESHEET)
    QApplication.processEvents()

    try:
        # This keeps my original button action while also showing the clicked state.
        action()
    finally:
        def restore_if_still_current() -> None:
            if button.property("_click_feedback_token") != token:
                return
            if button.styleSheet() == CLICK_FEEDBACK_STYLESHEET:
                button.setStyleSheet(str(original_stylesheet))
            button.setProperty("_click_feedback_token", None)
            button.setProperty("_click_feedback_original_stylesheet", None)

        QTimer.singleShot(delay_ms, restore_if_still_current)
