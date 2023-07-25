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

from datetime import date
from datetime import timedelta as td

from holidays.calendars.gregorian import (
    JAN,
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
    FRI,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class SouthAfrica(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    http://www.gov.za/about-sa/public-holidays
    https://en.wikipedia.org/wiki/Public_holidays_in_South_Africa
    """

    country = "ZA"
    special_holidays = {
        1999: (
            (JUN, 2, "National and provincial government elections"),
            (DEC, 31, "Y2K changeover"),
        ),
        2000: (JAN, 2, "Y2K changeover"),
        2004: (APR, 14, "National and provincial government elections"),
        2006: (MAR, 1, "Local government elections"),
        2008: (MAY, 2, "Public holiday by presidential decree"),
        2009: (APR, 22, "National and provincial government elections"),
        2011: (
            (MAY, 18, "Local government elections"),
            (DEC, 27, "Public holiday by presidential decree"),
        ),
        2014: (MAY, 7, "National and provincial government elections"),
        2016: (
            (AUG, 3, "Local government elections"),
            (DEC, 27, "Public holiday by presidential decree"),
        ),
        2019: (MAY, 8, "National and provincial government elections"),
        2021: (NOV, 1, "Municipal elections"),
        2022: (DEC, 27, "Public holiday by presidential decree"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        # As of 1995/1/1, whenever a public holiday falls on a Sunday,
        # it rolls over to the following Monday
        if self.observed and self._is_sunday(dt) and self._year >= 1995:
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        # Observed since 1910, with a few name changes
        if year <= 1909:
            return None

        super()._populate(year)

        self._add_observed(self._add_new_years_day("New Year's Day"))

        self._add_good_friday("Good Friday")

        self._add_easter_monday("Family Day" if year >= 1980 else "Easter Monday")

        if year <= 1951:
            name = "Dingaan's Day"
        elif year <= 1979:
            name = "Day of the Covenant"
        elif year <= 1994:
            name = "Day of the Vow"
        else:
            name = "Day of Reconciliation"
        self._add_observed(self._add_holiday(name, DEC, 16))

        self._add_christmas_day("Christmas Day")

        self._add_observed(
            self._add_christmas_day_two("Day of Goodwill" if year >= 1980 else "Boxing Day")
        )

        if year >= 1995:
            self._add_observed(self._add_holiday("Human Rights Day", MAR, 21))

            self._add_observed(self._add_holiday("Freedom Day", APR, 27))

            self._add_observed(self._add_labor_day("Workers' Day"))

            self._add_observed(self._add_holiday("Youth Day", JUN, 16))

            self._add_observed(self._add_holiday("National Women's Day", AUG, 9))

            self._add_observed(self._add_holiday("Heritage Day", SEP, 24))

        # Special holiday http://tiny.cc/za_y2k
        if self.observed and year == 2000:
            self._add_holiday("Y2K changeover (Observed)", JAN, 3)

        # Historic public holidays no longer observed
        if 1952 <= year <= 1973:
            self._add_holiday("Van Riebeeck's Day", APR, 6)
        elif 1980 <= year <= 1994:
            self._add_holiday("Founder's Day", APR, 6)

        if 1987 <= year <= 1989:
            self._add_holiday("Workers' Day", self._get_nth_weekday_of_month(1, FRI, MAY))

        if year <= 1993:
            self._add_ascension_thursday("Ascension Day")

        if year <= 1951:
            self._add_holiday("Empire Day", MAY, 24)

        if year <= 1960:
            self._add_holiday("Union Day", MAY, 31)
        elif year <= 1993:
            self._add_holiday("Republic Day", MAY, 31)

        if 1952 <= year <= 1960:
            self._add_holiday("Queen's Birthday", self._get_nth_weekday_of_month(2, MON, JUL))

        if 1961 <= year <= 1973:
            self._add_holiday("Family Day", JUL, 10)

        if year <= 1951:
            self._add_holiday("King's Birthday", self._get_nth_weekday_of_month(1, MON, AUG))

        if 1952 <= year <= 1979:
            self._add_holiday("Settlers' Day", self._get_nth_weekday_of_month(1, MON, SEP))

        if 1952 <= year <= 1993:
            self._add_holiday("Kruger Day", OCT, 10)


class ZA(SouthAfrica):
    pass


class ZAF(SouthAfrica):
    pass
