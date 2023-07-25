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

from holidays.calendars.gregorian import MAY, JUL
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Montenegro(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Montenegro
      - https://me.usembassy.gov/holiday-calendar/
      - https://publicholidays.eu/montenegro/2023-dates/
      - https://www.officeholidays.com/countries/montenegro/2023
    """

    country = "ME"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, calendar=JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_sunday(dt):
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days))

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        name = "New Year's Day"
        self._add_observed(self._add_new_years_day(name), days=+2)
        self._add_observed(self._add_new_years_day_two(name))

        # Orthodox Christmas Eve.
        self._add_christmas_eve("Orthodox Christmas Eve")

        # Orthodox Christmas.
        self._add_christmas_day("Orthodox Christmas")

        # Labour Day.
        name = "Labour Day"
        self._add_observed(self._add_labor_day(name), days=+2)
        self._add_observed(self._add_labor_day_two(name))

        # Good Friday.
        self._add_good_friday("Orthodox Good Friday")

        # Easter Sunday.
        self._add_easter_sunday("Orthodox Easter Sunday")

        # Easter Monday.
        self._add_easter_monday("Orthodox Easter Monday")

        # Independence Day.
        name = "Independence Day"
        may_21 = self._add_holiday(name, MAY, 21)
        self._add_observed(may_21, days=+2)
        self._add_observed(self._add_holiday(name, may_21 + td(days=+1)))

        # Statehood Day.
        name = "Statehood Day"
        jul_13 = self._add_holiday(name, JUL, 13)
        self._add_observed(jul_13, days=+2)
        self._add_observed(self._add_holiday(name, jul_13 + td(days=+1)))


class ME(Montenegro):
    pass


class MNE(Montenegro):
    pass
