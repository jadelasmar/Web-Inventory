# ---------- constants.py ----------
"""Project-wide constants and configuration helpers."""
from typing import List
import os

POS_CATEGORIES: List[str] = [
    "POS System",
    "Desktop Computer",
    "Server",
    "Receipt Printer",
    "Barcode Printer",
    "Laser Printer",
    "Toner/Ink",
    "UPS",
    "Cables",
    "Cash Drawer",
    "Barcode Reader",
    "Customer Display",
    "Keyboard/Mouse",
    "Other",
]

MOVEMENT_TYPES: List[str] = ["PURCHASE", "SALE", "ADJUSTMENT", "REPLACEMENT"]
LOW_STOCK_THRESHOLD_DEFAULT: int = 5
