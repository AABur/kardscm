"""Shared openpyxl styling constants for export modules."""

from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
HEADER_ALIGNMENT_NO_WRAP = Alignment(horizontal="center", vertical="center")
BOLD_FONT = Font(bold=True)
