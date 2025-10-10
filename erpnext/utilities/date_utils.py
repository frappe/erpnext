"""Small date utility helpers for ERPNext.

This module adds two tiny helpers:

- is_leap_year(year): Return True if `year` is a leap year using the
  Gregorian rules (divisible by 4, but not by 100 unless divisible by 400).
- days_in_year(year): Return 366 for leap years, otherwise 365.

These helpers are intentionally simple and have clear docstrings and
type-checking friendly signatures.
"""
from __future__ import annotations

from typing import Any


def is_leap_year(year: int) -> bool:
    """Return True if ``year`` is a leap year.

    Rules (Gregorian calendar):
    - Year divisible by 4 is a leap year
    - Except years divisible by 100 are not leap years
    - Except years divisible by 400 are leap years

    Args:
        year: Integer year (e.g., 2024)

    Returns:
        True if leap year, False otherwise.

    Raises:
        TypeError: If ``year`` is not an integer.
    """
    if not isinstance(year, int):
        raise TypeError("year must be an int")

    # Fast path
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    return year % 400 == 0


def days_in_year(year: int) -> int:
    """Return number of days in ``year`` (365 or 366).

    Args:
        year: Integer year

    Returns:
        366 if leap year else 365.

    Raises:
        TypeError: If ``year`` is not an integer.
    """
    return 366 if is_leap_year(year) else 365
