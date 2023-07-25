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

from datetime import timedelta as td

from holidays.calendars.gregorian import APR, SEP
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChineseCalendarHolidays, InternationalHolidays


class Vietnam(HolidayBase, ChineseCalendarHolidays, InternationalHolidays):
    """
    https://publicholidays.vn/
    http://vbpl.vn/TW/Pages/vbpqen-toanvan.aspx?ItemID=11013 Article.115
    https://www.timeanddate.com/holidays/vietnam/
    """

    country = "VN"

    def __init__(self, *args, **kwargs):
        ChineseCalendarHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)
        observed_dates = set()

        # New Year's Day
        observed_dates.add(self._add_new_years_day("International New Year's Day"))

        # Lunar New Year
        self._add_chinese_new_years_eve("Vietnamese New Year's Eve")
        self._add_chinese_new_years_day("Vietnamese New Year")
        self._add_chinese_new_years_day_two("The second day of Tet Holiday")
        self._add_chinese_new_years_day_three("The third day of Tet Holiday")
        self._add_chinese_new_years_day_four("The forth day of Tet Holiday")
        self._add_chinese_new_years_day_five("The fifth day of Tet Holiday")

        # Vietnamese Kings' Commemoration Day
        # https://en.wikipedia.org/wiki/H%C3%B9ng_Kings%27_Festival
        if year >= 2007:
            observed_dates.add(self._add_hung_kings_day("Hung Kings Commemoration Day"))

        # Liberation Day/Reunification Day
        observed_dates.add(self._add_holiday("Liberation Day/Reunification Day", APR, 30))

        # International Labor Day
        observed_dates.add(self._add_labor_day("International Labor Day"))

        # Independence Day
        observed_dates.add(self._add_holiday("Independence Day", SEP, 2))

        if self.observed:
            for dt in sorted(observed_dates):
                if not self._is_weekend(dt):
                    continue
                next_workday = dt + td(days=+1)
                while self._is_weekend(next_workday) or next_workday in observed_dates:
                    next_workday += td(days=+1)
                observed_dates.add(self._add_holiday(f"{self[dt]} (Observed)", next_workday))


class VN(Vietnam):
    pass


class VNM(Vietnam):
    pass
