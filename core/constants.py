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

MOVEMENT_TYPES: List[str] = [
    "PURCHASE",      # Buying new stock
    "SALE",         # Selling to customer permanently
    "ADJUSTMENT",   # Manual stock correction
    "RECEIVED",     # Receive printer from customer to work on (stock +)
    "ISSUED"        # Give temp printer or return fixed printer (stock -)
]
LOW_STOCK_THRESHOLD_DEFAULT: int = 5
