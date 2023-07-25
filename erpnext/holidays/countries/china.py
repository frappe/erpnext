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

from holidays.calendars.gregorian import OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChineseCalendarHolidays, InternationalHolidays


class China(HolidayBase, ChineseCalendarHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_China
    """

    country = "CN"

    def __init__(self, *args, **kwargs):
        ChineseCalendarHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1949:
            return None
        super()._populate(year)

        self._add_new_years_day("New Year's Day")

        name = "Labour Day"
        self._add_labor_day(name)
        if 2000 <= year <= 2007:
            self._add_labor_day_two(name)
            self._add_labor_day_three(name)

        name = "Chinese New Year (Spring Festival)"
        self._add_chinese_new_years_day(name)
        self._add_chinese_new_years_day_two(name)
        if 2008 <= year <= 2013:
            self._add_chinese_new_years_eve(name)
        else:
            self._add_chinese_new_years_day_three(name)

        name = "National Day"
        self._add_holiday(name, OCT, 1)
        self._add_holiday(name, OCT, 2)
        if year >= 2000:
            self._add_holiday(name, OCT, 3)

        if year >= 2008:
            self._add_qingming_festival("Tomb-Sweeping Day")
            self._add_dragon_boat_festival("Dragon Boat Festival")
            self._add_mid_autumn_festival("Mid-Autumn Festival")


class CN(China):
    pass


class CHN(China):
    pass
