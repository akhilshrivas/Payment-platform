"""
Utility functions shared across the project.
"""

import uuid
from decimal import Decimal


def generate_reference(prefix: str = "TXN") -> str:
    """
    Generate a unique reference string.
    Example: TXN-550e8400-e29b-41d4-a716
    """
    unique_id = str(uuid.uuid4()).replace("-", "").upper()[:16]
    return f"{prefix}-{unique_id}"


def paise_to_inr(paise: int) -> Decimal:
    """Convert paise (integer) to INR Decimal."""
    return Decimal(paise) / Decimal(100)


def inr_to_paise(inr: Decimal) -> int:
    """Convert INR Decimal to paise (integer) for Razorpay."""
    return int(inr * 100)


def mask_account(value: str, visible: int = 4) -> str:
    """Mask sensitive strings, showing only the last N characters."""
    if len(value) <= visible:
        return value
    return "*" * (len(value) - visible) + value[-visible:]
