from __future__ import annotations

from attune.dashboard.theme.tokens import PALETTE, Palette


def build_stylesheet(palette: Palette = PALETTE) -> str:
    """Dark glassmorphism QSS per docs/architecture/07-ui-wireframes.md.

    QSS has no backdrop-filter/blur, so "glass" is approximated with a
    translucent fill + hairline border, same visual family as the wireframe
    spec without needing an unsupported CSS feature.
    """
    return f"""
    QMainWindow, QWidget#RootWindow {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {palette.background_top}, stop:1 {palette.background_bottom}
        );
        color: {palette.text_primary};
        font-family: {palette.font_family};
    }}

    QWidget {{
        color: {palette.text_primary};
        font-family: {palette.font_family};
    }}

    QLabel {{
        background: transparent;
    }}

    QLabel[role="title"] {{
        font-size: 15px;
        font-weight: 600;
        color: {palette.text_primary};
    }}

    QLabel[role="secondary"] {{
        font-size: 12px;
        color: {palette.text_secondary};
    }}

    QLabel[role="muted"] {{
        font-size: 11px;
        color: {palette.text_muted};
    }}

    QLabel[role="metric"] {{
        font-size: 32px;
        font-weight: 700;
        color: {palette.text_primary};
    }}

    QFrame#Card {{
        background: {palette.glass_fill};
        border: 1px solid {palette.glass_border};
        border-radius: 14px;
    }}

    QFrame#NavRail {{
        background: rgba(0, 0, 0, 0.2);
        border-right: 1px solid {palette.glass_border};
    }}

    QPushButton#NavButton {{
        text-align: left;
        padding: 10px 14px;
        border-radius: 10px;
        border: none;
        background: transparent;
        color: {palette.text_secondary};
        font-size: 13px;
    }}

    QPushButton#NavButton:hover {{
        background: {palette.glass_fill_hover};
        color: {palette.text_primary};
    }}

    QPushButton#NavButton:checked {{
        background: {palette.glass_fill_hover};
        color: {palette.text_primary};
        font-weight: 600;
    }}

    QPushButton#PrimaryButton {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {palette.accent_indigo}, stop:1 {palette.accent_teal}
        );
        color: white;
        border: none;
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
    }}

    QPushButton#PrimaryButton:disabled {{
        background: {palette.glass_fill};
        color: {palette.text_muted};
    }}

    QPushButton#SecondaryButton {{
        background: {palette.glass_fill};
        border: 1px solid {palette.glass_border};
        border-radius: 10px;
        padding: 8px 18px;
        color: {palette.text_primary};
    }}

    QPushButton#SecondaryButton:hover {{
        background: {palette.glass_fill_hover};
    }}

    QListWidget, QTableWidget {{
        background: transparent;
        border: none;
        color: {palette.text_primary};
    }}

    QListWidget::item {{
        padding: 6px 4px;
        border-bottom: 1px solid {palette.glass_border};
    }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {palette.glass_fill};
        border: 1px solid {palette.glass_border};
        border-radius: 8px;
        padding: 6px 10px;
        color: {palette.text_primary};
    }}

    QCheckBox {{
        color: {palette.text_primary};
        spacing: 8px;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {palette.glass_border};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        background: {palette.accent_teal};
        width: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}

    QScrollBar::handle:vertical {{
        background: {palette.glass_border};
        border-radius: 4px;
        min-height: 24px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
