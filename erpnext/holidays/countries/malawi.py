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

from holidays.calendars.gregorian import JAN, MAR, MAY, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Malawi(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.officeholidays.com/countries/malawi
    https://www.timeanddate.com/holidays/malawi/
    """

    country = "MW"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_weekend(dt):
            self._add_holiday(
                "%s (Observed)" % self[dt], dt + td(+2 if self._is_saturday(dt) else days)
            )

    def _populate(self, year):
        # Observed since 2000
        if year <= 1999:
            return None

        super()._populate(year)

        self._add_observed(self._add_new_years_day("New Year's Day"))

        self._add_observed(self._add_holiday("John Chilembwe Day", JAN, 15))

        self._add_observed(self._add_holiday("Martyrs Day", MAR, 3))

        self._add_good_friday("Good Friday")

        self._add_easter_monday("Easter Monday")

        self._add_observed(self._add_labor_day("Labour Day"))

        self._add_observed(self._add_holiday("Kamuzu Day", MAY, 14))

        self._add_observed(self._add_holiday("Independence Day", JUL, 6))

        self._add_observed(self._add_holiday("Mother's Day", OCT, 15))

        self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)

        self._add_observed(self._add_christmas_day_two("Boxing Day"), days=+2)


class MW(Malawi):
    pass


class MWI(Malawi):
    pass
