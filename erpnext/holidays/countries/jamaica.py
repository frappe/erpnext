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

from holidays.calendars.gregorian import MAY, AUG, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Jamaica(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Jamaica
    https://www.mlss.gov.jm/wp-content/uploads/2017/11/The-Holidays-Public-General-Act.pdf
    """

    country = "JM"

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, include_sat: bool = False, days: int = +1) -> None:
        if not self.observed:
            return None
        if self._is_sunday(dt) or (include_sat and self._is_saturday(dt)):
            self._add_holiday(
                "%s (Observed)" % self[dt], dt + td(days=+2 if self._is_saturday(dt) else days)
            )

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day
        self._add_observed(self._add_new_years_day("New Year's Day"))

        # Ash Wednesday
        self._add_ash_wednesday("Ash Wednesday")

        # Good Friday
        self._add_good_friday("Good Friday")

        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # National Labour Day
        self._add_observed(self._add_holiday("National Labour Day", MAY, 23), include_sat=True)

        # Emancipation Day
        if year >= 1998:
            self._add_observed(self._add_holiday("Emancipation Day", AUG, 1))

        # Independence Day
        self._add_observed(self._add_holiday("Independence Day", AUG, 6))

        # National Heroes Day
        self._add_holiday("National Heroes Day", self._get_nth_weekday_of_month(3, MON, OCT))

        # Christmas Day
        self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)

        # Boxing Day
        self._add_observed(self._add_christmas_day_two("Boxing Day"))


class JM(Jamaica):
    pass


class JAM(Jamaica):
    pass
