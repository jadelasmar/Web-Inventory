# ---------- constants.py ----------
"""Project-wide constants and configuration helpers."""
from typing import List

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

PARTY_TYPES: List[str] = [
    "Supplier",
    "Customer",
    "Other",
]

# Sidebar menu labels (keep in sync across app and sidebar)
MENU_DASHBOARD = "\U0001F4C8 Dashboard"
MENU_INVENTORY = "\U0001F5C2\ufe0f View Inventory"
MENU_ALERTS = "\U0001F6A8 Stock Alerts"
MENU_MOVEMENTS = "\U0001F501 Movement Log"
MENU_ADD_PRODUCT = "\u2795 Add Product"
MENU_STOCK_MOVEMENT = "\U0001F4E6 Stock Movement"
MENU_USER_MANAGEMENT = "\U0001F9D1\u200D\U0001F4BB User Management"
MENU_PARTIES = "\U0001F465 Customers & Suppliers"
