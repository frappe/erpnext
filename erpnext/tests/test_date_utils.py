import pytest

from erpnext.utilities import date_utils


def test_common_leap_years():
    assert date_utils.is_leap_year(2024) is True
    assert date_utils.is_leap_year(2020) is True
    assert date_utils.days_in_year(2024) == 366


def test_common_non_leap_years():
    assert date_utils.is_leap_year(2023) is False
    assert date_utils.days_in_year(2023) == 365


def test_century_rules():
    # 1900 is not a leap year (divisible by 100, not by 400)
    assert date_utils.is_leap_year(1900) is False
    assert date_utils.days_in_year(1900) == 365

    # 2000 is a leap year (divisible by 400)
    assert date_utils.is_leap_year(2000) is True
    assert date_utils.days_in_year(2000) == 366


def test_invalid_input():
    with pytest.raises(TypeError):
        date_utils.is_leap_year("2024")
