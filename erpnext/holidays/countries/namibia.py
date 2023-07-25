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

from holidays.calendars.gregorian import JAN, FEB, MAR, MAY, AUG, SEP, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Namibia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.officeholidays.com/countries/namibia
    https://www.timeanddate.com/holidays/namibia/

    """

    country = "NA"
    special_holidays = {
        # https://gazettes.africa/archive/na/1999/na-government-gazette-dated-1999-11-22-no-2234.pdf
        1999: (DEC, 31, "Y2K changeover"),
        2000: (JAN, 3, "Y2K changeover"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        # https://tinyurl.com/lacorg5835
        # As of 1991/2/1, whenever a public holiday falls on a Sunday,
        # it rolls over to the monday, unless that monday is already
        # a public holiday.
        if self.observed and self._is_sunday(dt) and dt >= date(1991, FEB, 1):
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        if year <= 1989:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_observed(self._add_new_years_day("New Year's Day"))

        # Independence Day.
        self._add_observed(self._add_holiday("Independence Day", MAR, 21))

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # Workers' Day.
        self._add_observed(self._add_labor_day("Workers' Day"))

        # Cassinga Day.
        self._add_observed(self._add_holiday("Cassinga Day", MAY, 4))

        # Africa Day.
        self._add_observed(self._add_africa_day("Africa Day"))

        # Ascension Day.
        self._add_ascension_thursday("Ascension Day")

        # Heroes' Day.
        self._add_observed(self._add_holiday("Heroes' Day", AUG, 26))

        # http://www.lac.org.na/laws/2004/3348.pdf
        self._add_observed(
            self._add_holiday(
                "Day of the Namibian Women and International Human Rights Day"
                if year >= 2005
                else "International Human Rights Day",
                SEP,
                10,
            )
        )

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Family Day.
        self._add_observed(self._add_christmas_day_two("Family Day"))


class NA(Namibia):
    pass


class NAM(Namibia):
    pass
