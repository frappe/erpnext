#  python-holidays
#  ---------------
#  A fast, efficient Python library for generating country, province and state
#  specific sets of holidays on the fly. It aims to make determining whether a
#  specific date is a holiday as fast and flexible as possible.
#
#  Authors: dr-prodigy <dr.prodigy.github@gmail.com> (c) 2017-2023
#           ryanss <ryanssdev@icloud.com> (c) 2014-2017
#  Website: https://github.com/dr-prodigy/python-holidays
#  License: MIT (see LICENSE file)

# flake8: noqa: F401

from holidays.calendars.gregorian import (
    JAN,
    FEB,
    MAR,
    APR,
    MAY,
    JUN,
    JUL,
    AUG,
    SEP,
    OCT,
    NOV,
    DEC,
    MON,
    TUE,
    WED,
    THU,
    FRI,
    SAT,
    SUN,
    WEEKEND,
)

HOLIDAY_NAME_DELIMITER = "; "  # Holiday names separator.

# Supported holiday categories.
BANK = "bank"
EXTENDED = "extended"
GOVERNMENT = "government"
HALF_DAY = "half_day"
PUBLIC = "public"
SCHOOL = "school"
WORKDAY = "workday"

CHINESE = "chinese"
CHRISTIAN = "christian"
HEBREW = "hebrew"
HINDU = "hindu"
ISLAMIC = "islamic"

ALL_CATEGORIES = {
    BANK,
    CHINESE,
    CHRISTIAN,
    EXTENDED,
    GOVERNMENT,
    HALF_DAY,
    HEBREW,
    HINDU,
    ISLAMIC,
    PUBLIC,
    SCHOOL,
    WORKDAY,
}
