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

from holidays.calendars.gregorian import JUL, SEP, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Botswana(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.gov.bw/public-holidays
    https://publicholidays.africa/botswana/2021-dates/
    https://www.timeanddate.com/holidays/botswana/
    http://www.ilo.org/dyn/travail/docs/1766/Public%20Holidays%20Act.pdf
    """

    country = "BW"
    special_holidays = {2019: (JUL, 2, "Public Holiday")}

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_sunday(dt) and self._year >= 1995:
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=days))

    def _populate(self, year):
        if year <= 1965:
            return None

        super()._populate(year)

        self._add_observed(self._add_new_years_day("New Year's Day"), days=+2)
        self._add_observed(self._add_new_years_day_two("New Year's Day Holiday"))

        # Easter and easter related calculations
        self._add_good_friday("Good Friday")
        self._add_holy_saturday("Holy Saturday")
        self._add_easter_monday("Easter Monday")
        self._add_ascension_thursday("Ascension Day")

        may_1 = self._add_labor_day("Labour Day")
        self._add_observed(may_1)
        if self.observed and year >= 2016 and self._is_saturday(may_1):
            self._add_labor_day_three("Labour Day Holiday")

        self._add_observed(self._add_holiday("Sir Seretse Khama Day", JUL, 1))

        july_3rd_monday = self._add_holiday(
            "President's Day", self._get_nth_weekday_of_month(3, MON, JUL)
        )
        self._add_holiday("President's Day Holiday", july_3rd_monday + td(days=+1))

        sep_30 = self._add_holiday("Botswana Day", SEP, 30)
        self._add_observed(sep_30, days=+2)
        self._add_observed(self._add_holiday("Botswana Day Holiday", sep_30 + td(days=+1)))

        self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)
        dec_26 = self._add_christmas_day_two("Boxing Day")
        self._add_observed(dec_26)

        if self.observed and year >= 2016 and self._is_saturday(dec_26):
            self._add_holiday("Boxing Day Holiday", dec_26 + td(days=+2))


class BW(Botswana):
    pass


class BWA(Botswana):
    pass
