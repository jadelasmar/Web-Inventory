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
# MUST be set via environment variable or Streamlit secrets - no default provided.
# For local dev, set ADMIN_PASSWORD environment variable.
# For Streamlit Cloud, set in secrets as ADMIN_PASSWORD (top level, not nested)
try:
    import streamlit as st
    ADMIN_PASSWORD: str = st.secrets.get("ADMIN_PASSWORD", os.getenv(
        "ADMIN_PASSWORD",
        "CHANGE_ME_RANDOM_",
    ))
except:
    ADMIN_PASSWORD: str = os.getenv(
        "ADMIN_PASSWORD",
        "CHANGE_ME_RANDOM_",
    )
