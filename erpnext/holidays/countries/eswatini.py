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

import warnings
from datetime import date
from datetime import timedelta as td

from holidays.calendars.gregorian import JAN, APR, JUL, SEP, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Eswatini(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://swazilii.org/sz/legislation/act/1938/71
    https://www.officeholidays.com/countries/swaziland
    """

    country = "SZ"
    special_holidays = {
        # https://mg.co.za/article/1999-12-09-swaziland-declares-bank-holidays/
        1999: (DEC, 31, "Y2K changeover"),
        2000: (JAN, 3, "Y2K changeover"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        # As of 2021/1/1, whenever a public holiday falls on a Sunday
        # it rolls over to the following Monday
        if self.observed and self._is_sunday(dt) and self._year >= 2021:
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=days))

    def _populate(self, year):
        # Observed since 1939
        if year <= 1938:
            return None

        super()._populate(year)

        self._add_observed(self._add_new_years_day("New Year's Day"))

        self._add_good_friday("Good Friday")

        self._add_easter_monday("Easter Monday")

        self._add_ascension_thursday("Ascension Day")

        if year >= 1987:
            apr_19 = self._add_holiday("King's Birthday", APR, 19)
            self._add_observed(apr_19, days=+2 if apr_19 == self._easter_sunday else +1)

        if year >= 1969:
            apr_25 = self._add_holiday("National Flag Day", APR, 25)
            self._add_observed(apr_25, days=+2 if apr_25 == self._easter_sunday else +1)

        self._add_observed(self._add_labor_day("Worker's Day"))

        if year >= 1983:
            self._add_observed(self._add_holiday("Birthday of Late King Sobhuza", JUL, 22))

        self._add_observed(self._add_holiday("Independence Day", SEP, 6))

        self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)

        self._add_observed(self._add_christmas_day_two("Boxing Day"))


class Swaziland(Eswatini):
    def __init__(self, *args, **kwargs) -> None:
        warnings.warn("Swaziland is deprecated, use Eswatini instead.", DeprecationWarning)

        super().__init__(*args, **kwargs)


class SZ(Eswatini):
    pass


class SZW(Eswatini):
    pass
