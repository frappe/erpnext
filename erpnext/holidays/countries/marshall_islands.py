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

from holidays.calendars.gregorian import MAR, MAY, JUL, SEP, NOV, DEC, FRI
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class HolidaysMH(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://rmiparliament.org/cms/component/content/article/14-pressrelease/49-important-public-holidays.html?Itemid=101
    https://www.rmiembassyus.org/country-profile#:~:text=national%20holidays
    """

    country = "MH"

    # Special Holidays

    # General Election Day
    election_day = "General Election Day"

    special_holidays = {
        1995: (NOV, 20, election_day),
        1999: (NOV, 22, election_day),
        2003: (NOV, 17, election_day),
        2007: (NOV, 19, election_day),
        2011: (NOV, 21, election_day),
        2015: (NOV, 16, election_day),
        2019: (NOV, 18, election_day),
        2023: (NOV, 20, election_day),
    }

    def _add_observed(self, dt: date) -> None:
        """
        If fall on Sunday, an observed holiday marked with suffix " Holiday" will be added.
        """
        if self.observed and self._is_sunday(dt):
            self._add_holiday("%s Holiday" % self[dt], dt + td(days=+1))

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        if year <= 2019:
            warnings.warn(
                "Years before 2020 are not available for the Marshall Islands (MH).", Warning
            )

        # New Year's Day
        self._add_observed(self._add_new_years_day("New Year's Day"))

        # Nuclear Victims Remembrance Day
        self._add_observed(self._add_holiday("Nuclear Victims Remembrance Day", MAR, 1))

        # Good Friday
        self._add_good_friday("Good Friday")

        # Constitution Day
        self._add_observed(self._add_holiday("Constitution Day", MAY, 1))

        # Fisherman's Day
        self._add_holiday("Fisherman's Day", self._get_nth_weekday_of_month(1, FRI, JUL))

        # Dri-jerbal Day
        self._add_holiday("Dri-jerbal Day", self._get_nth_weekday_of_month(1, FRI, SEP))

        # Manit Day
        self._add_holiday("Manit Day", self._get_nth_weekday_of_month(-1, FRI, SEP))

        # President's Day
        self._add_observed(self._add_holiday("President's Day", NOV, 17))

        # Gospel Day
        self._add_holiday("Gospel Day", self._get_nth_weekday_of_month(1, FRI, DEC))

        # Christmas Day
        name = "Christmas Day"
        if year == 2021:
            # special case
            self._add_holiday(name, DEC, 24)
        else:
            self._add_observed(self._add_christmas_day(name))


class MH(HolidaysMH):
    pass


class MHL(HolidaysMH):
    pass


class MarshallIslands(HolidaysMH):
    pass
