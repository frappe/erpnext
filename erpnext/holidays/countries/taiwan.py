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

from holidays.calendars.gregorian import FEB, APR, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChineseCalendarHolidays, InternationalHolidays


class Taiwan(HolidayBase, ChineseCalendarHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Taiwan
    """

    country = "TW"

    def __init__(self, *args, **kwargs):
        ChineseCalendarHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1911:
            return None
        super()._populate(year)

        # New Year's Day
        self._add_new_years_day("Founding of the Republic of China (New Year's Day)")

        self._add_chinese_new_years_eve("Chinese New Year's Eve")

        name = "Spring Festival"
        self._add_chinese_new_years_day(name)
        self._add_chinese_new_years_day_two(name)
        self._add_chinese_new_years_day_three(name)
        if year == 2021:
            self._add_chinese_new_years_day_four(name)
            self._add_chinese_new_years_day_five(name)

        self._add_holiday("Children's Day", APR, 4)

        self._add_dragon_boat_festival("Dragon Boat Festival")
        self._add_mid_autumn_festival("Mid-Autumn Festival")

        name = "National Day"
        self._add_holiday(name, OCT, 10)
        self._add_holiday(name, OCT, 11)

        if year >= 1948:
            self._add_holiday("Peace Memorial Day", FEB, 28)


class TW(Taiwan):
    pass


class TWN(Taiwan):
    pass
