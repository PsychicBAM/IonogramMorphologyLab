"""Theme-aware UI tokens for Active Source cards and related surfaces (Phase 4B.2d)."""

from __future__ import annotations

from typing import Literal

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

ThemeName = Literal["light", "dark"]


def resolve_theme_name(preference: str | None = None) -> ThemeName:
    """Resolve light/dark from settings preference or system palette."""
    pref = (preference or "system").strip().lower()
    if pref in ("dark", "light"):
        return pref  # type: ignore[return-value]
    app = QApplication.instance()
    if app is None:
        return "light"
    window = app.palette().color(QPalette.ColorRole.Window)
    # Relative luminance heuristic
    luma = 0.2126 * window.redF() + 0.7152 * window.greenF() + 0.0722 * window.blueF()
    return "dark" if luma < 0.45 else "light"


def source_card_tokens(theme: ThemeName) -> dict[str, str]:
    """Readable contrast tokens for ActiveSourceCard / ImportFileRow."""
    if theme == "dark":
        return {
            "bg": "#2a2d33",
            "bg_alt": "#32363e",
            "border": "#5a6270",
            "text": "#e8eaed",
            "text_muted": "#b0b6c0",
            "accent": "#7cb3ff",
            "badge_active_bg": "#1e4d2b",
            "badge_active_fg": "#b6f0c4",
            "badge_inactive_bg": "#3a3f48",
            "badge_inactive_fg": "#d0d4dc",
            "badge_aux_bg": "#3d3420",
            "badge_aux_fg": "#f0d78c",
            "badge_bad_bg": "#4a2222",
            "badge_bad_fg": "#f0a8a8",
            "btn_bg": "#3a404c",
            "btn_fg": "#e8eaed",
            "btn_border": "#6a7382",
            "btn_hover": "#4a5160",
            "btn_pressed": "#2e333c",
            "btn_disabled_bg": "#2e3238",
            "btn_disabled_fg": "#7a808a",
            "focus": "#8ab4ff",
            "warn_bg": "#3d3420",
            "warn_fg": "#f0d78c",
            "warn_border": "#8a7040",
            "error_fg": "#f0a8a8",
        }
    return {
        "bg": "#f4f5f7",
        "bg_alt": "#ffffff",
        "border": "#9aa3b0",
        "text": "#1a1f28",
        "text_muted": "#4a5564",
        "accent": "#1657c2",
        "badge_active_bg": "#d8f0df",
        "badge_active_fg": "#0d4a1f",
        "badge_inactive_bg": "#e4e7ec",
        "badge_inactive_fg": "#2a3140",
        "badge_aux_bg": "#fff3d6",
        "badge_aux_fg": "#5c4300",
        "badge_bad_bg": "#fde0e0",
        "badge_bad_fg": "#7a1515",
        "btn_bg": "#e8ebf0",
        "btn_fg": "#1a1f28",
        "btn_border": "#7a8494",
        "btn_hover": "#d5dae3",
        "btn_pressed": "#c4cad6",
        "btn_disabled_bg": "#eceef2",
        "btn_disabled_fg": "#8a93a1",
        "focus": "#1657c2",
        "warn_bg": "#fff8e8",
        "warn_fg": "#5c4300",
        "warn_border": "#a67c00",
        "error_fg": "#a40",
    }


def source_surface_qss(object_name: str, theme: ThemeName | None = None) -> str:
    t = source_card_tokens(theme or resolve_theme_name())
    return f"""
    {object_name} {{
        background: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        color: {t['text']};
    }}
    {object_name} QLabel {{
        color: {t['text']};
        background: transparent;
    }}
    {object_name} QLabel[muted="true"] {{
        color: {t['text_muted']};
    }}
    {object_name} QToolButton {{
        color: {t['accent']};
        background: transparent;
        border: none;
        text-align: left;
    }}
    {object_name} QPushButton {{
        background: {t['btn_bg']};
        color: {t['btn_fg']};
        border: 1px solid {t['btn_border']};
        border-radius: 3px;
        padding: 4px 8px;
    }}
    {object_name} QPushButton:hover {{
        background: {t['btn_hover']};
    }}
    {object_name} QPushButton:pressed {{
        background: {t['btn_pressed']};
    }}
    {object_name} QPushButton:disabled {{
        background: {t['btn_disabled_bg']};
        color: {t['btn_disabled_fg']};
        border-color: {t['btn_disabled_fg']};
    }}
    {object_name} QPushButton:focus {{
        border: 2px solid {t['focus']};
    }}
    """


def apply_app_theme(app: QApplication | None, preference: str | None = None) -> ThemeName:
    """Apply a minimal light/dark palette so system 'dark' is usable with our cards."""
    theme = resolve_theme_name(preference)
    if app is None:
        return theme
    pal = app.palette()
    if theme == "dark":
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e2126"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#e8eaed"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#252930"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2d33"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#e8eaed"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3a404c"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e8eaed"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#3d6db5"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#32363e"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#e8eaed"))
        pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#7a808a"))
        pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#7a808a"))
        pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#7a808a"))
    else:
        pal = QApplication.style().standardPalette() if QApplication.style() else pal
        pal.setColor(QPalette.ColorRole.Window, QColor("#f0f2f5"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1a1f28"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1a1f28"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e8ebf0"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1a1f28"))
    app.setPalette(pal)
    return theme


def refresh_themed_widget(widget: QWidget, object_name: str, preference: str | None = None) -> None:
    theme = resolve_theme_name(preference)
    widget.setObjectName(object_name)
    widget.setStyleSheet(source_surface_qss(f"QFrame#{object_name}", theme))
