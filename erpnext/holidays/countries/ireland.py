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

from holidays.calendars.gregorian import FEB, MAR, MAY, JUN, AUG, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Ireland(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Official holidays in Ireland, as declared in the Citizen's Information
    bulletin:
    https://www.citizensinformation.ie/en/employment/employment_rights_and_conditions/leave_and_holidays/public_holidays_in_ireland.html
    """

    country = "IE"
    special_holidays = {
        2022: (MAR, 18, "Day of Remembrance and Recognition"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_weekend(dt):
            self._add_holiday(
                "%s (Observed)" % self[dt], dt + td(days=+2 if self._is_saturday(dt) else days)
            )

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # St. Brigid's Day.
        if year >= 2023:
            dt = date(year, FEB, 1)
            self._add_holiday(
                "St. Brigid's Day",
                dt if self._is_friday(dt) else self._get_nth_weekday_from(1, MON, dt),
            )

        # St. Patrick's Day.
        self._add_observed(self._add_holiday("St. Patrick's Day", MAR, 17))

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # May Day.
        if year >= 1978:
            self._add_holiday(
                "May Day",
                date(year, MAY, 8)
                if year == 1995
                else self._get_nth_weekday_of_month(1, MON, MAY),
            )

        # June Bank holiday.
        self._add_holiday("June Bank Holiday", self._get_nth_weekday_of_month(1, MON, JUN))

        # Summer Bank holiday.
        self._add_holiday("August Bank Holiday", self._get_nth_weekday_of_month(1, MON, AUG))

        # October Bank Holiday.
        self._add_holiday("October Bank Holiday", self._get_nth_weekday_of_month(-1, MON, OCT))

        # Christmas Day.
        self._add_observed(self._add_christmas_day("Christmas Day"))

        # St. Stephen's Day.
        self._add_observed(self._add_christmas_day_two("St. Stephen's Day"), days=+2)


class IE(Ireland):
    pass


class IRL(Ireland):
    pass
