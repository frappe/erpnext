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

from holidays.calendars.gregorian import MAR, APR, MAY, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Lesotho(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Lesotho
    - https://www.ilo.org/dyn/travail/docs/2093/Public%20Holidays%20Act%201995.pdf
    - https://www.timeanddate.com/holidays/lesotho/
    """

    country = "LS"
    special_holidays = {
        2002: (MAY, 25, "Africa Day"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1995:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Moshoeshoe's Day.
        self._add_holiday("Moshoeshoe's Day", MAR, 11)

        if year <= 2002:
            # Heroes Day.
            self._add_holiday("Heroes Day", APR, 4)

        if year >= 2003:
            # Africa/Heroes Day.
            self._add_africa_day("Africa/Heroes Day")

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # Workers' Day.
        self._add_labor_day("Workers' Day")

        # Ascension Day.
        self._add_ascension_thursday("Ascension Day")

        # https://en.wikipedia.org/wiki/Letsie_III
        # King's Birthday.
        self._add_holiday("King's Birthday", *((JUL, 17) if year >= 1998 else (MAY, 2)))

        # Independence Day.
        self._add_holiday("Independence Day", OCT, 4)

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Boxing Day.
        self._add_christmas_day_two("Boxing Day")


class LS(Lesotho):
    pass


class LSO(Lesotho):
    pass
