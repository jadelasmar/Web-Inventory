# ---------- constants.py ----------
"""Project-wide constants and configuration helpers."""
from typing import List
import os
from pathlib import Path

# Optionally load environment variables from a local .env file
# if python-dotenv is installed. This keeps local development easy.
try:
    from dotenv import load_dotenv  # type: ignore

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    # dotenv is optional; fall back to environment variables.
    pass

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

# Read admin password from environment for security. 
# Default is for LOCAL DEVELOPMENT ONLY. Set ADMIN_PASSWORD in Streamlit secrets.
ADMIN_PASSWORD: str = os.getenv(
    "ADMIN_PASSWORD",
    "admin123",  # Only for local dev - change in production via environment variable
)
