from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    """Design tokens from docs/architecture/07-ui-wireframes.md."""

    background_top: str = "#0B0D10"
    background_bottom: str = "#14171C"

    glass_fill: str = "rgba(255, 255, 255, 0.04)"
    glass_border: str = "rgba(255, 255, 255, 0.08)"
    glass_fill_hover: str = "rgba(255, 255, 255, 0.07)"

    text_primary: str = "#F5F6F7"
    text_secondary: str = "#9AA1AC"
    text_muted: str = "#5C6370"

    accent_indigo: str = "#6C5CE7"
    accent_teal: str = "#00D2A0"

    good: str = "#2ECC71"
    caution: str = "#F5A623"
    alert: str = "#FF5A5F"

    font_family: str = '"Inter", "Segoe UI", "SF Pro Display", sans-serif'


PALETTE = Palette()
