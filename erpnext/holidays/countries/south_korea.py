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

from holidays.calendars import _CustomChineseCalendar
from holidays.calendars.gregorian import JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, SAT, SUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import (
    ChineseCalendarHolidays,
    ChristianHolidays,
    InternationalHolidays,
)


class SouthKorea(HolidayBase, ChineseCalendarHolidays, ChristianHolidays, InternationalHolidays):
    """
    1. https://publicholidays.co.kr/ko/2020-dates/
    2. https://en.wikipedia.org/wiki/Public_holidays_in_South_Korea
    3. https://www.law.go.kr/%EB%B2%95%EB%A0%B9/%EA%B4%80%EA%B3%B5%EC%84%9C%EC%9D%98%20%EA%B3%B5%ED%9C%B4%EC%9D%BC%EC%97%90%20%EA%B4%80%ED%95%9C%20%EA%B7%9C%EC%A0%95  # noqa

    According to (3), the alt holidays in Korea are as follows:
    The alt holiday means next first non holiday after the holiday.
    Independence movement day, Liberation day, National Foundation Day,
    Hangul Day, Children's Day, Birthday of the Buddha, Christmas Day have alt holiday if they fell on Saturday or Sunday.
    Lunar New Year's Day, Korean Mid Autumn Day have alt holiday if they fell
    on only sunday.

    """

    country = "KR"
    special_holidays = {
        # Just for year 2020 - since 2020.08.15 is Sat, the government
        # decided to make 2020.08.17 holiday, yay
        2020: (AUG, 17, "Alternative public holiday"),
    }

    def __init__(self, *args, **kwargs):
        ChineseCalendarHolidays.__init__(self, calendar=SouthKoreaLunisolarCalendar())
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_with_alt_holiday(
        self,
        hol_name: str,
        hol_date: date,
        add_hol: bool = True,
        since: int = 2021,
        include_sat: bool = True,
    ) -> None:
        """Add alternative holiday on first day from the date provided
        that's not already a another holiday nor a weekend.

        :param hol_name:
           The name of the holiday.

        :param hol_date:
           The date of the holiday.

        :param add_hol:
           Add the holiday itself, not alternative only

        :param since:
           Year starting from which alt holiday should be added

        :param include_sat:
           Whether Saturday is to be considered a weekend in addition to
           Sunday.
        """
        if add_hol:
            self._add_holiday(hol_name, hol_date)

        if not self.observed:
            return None

        target_weekday = {SUN}
        if include_sat:
            target_weekday.add(SAT)
        if (
            hol_date.weekday() in target_weekday or len(self.get_list(hol_date)) > 1
        ) and hol_date.year >= since:
            hol_date += td(days=+1)
            while hol_date.weekday() in target_weekday or hol_date in self:
                hol_date += td(days=+1)
            self._add_holiday("Alternative holiday of %s" % hol_name, hol_date)

    def _populate(self, year):
        if year <= 1947:
            return None
        super()._populate(year)

        # New Year's Day
        self._add_new_years_day("New Year's Day")

        preceding_day = "The day preceding of %s"
        second_day = "The second day of %s"

        # Lunar New Year
        name = "Lunar New Year's Day"
        new_year_date = self._add_chinese_new_years_day(name)
        self._add_chinese_new_years_eve(preceding_day % name)
        self._add_chinese_new_years_day_two(second_day % name)

        for delta in (-1, 0, +1):
            self._add_with_alt_holiday(
                name, new_year_date + td(days=delta), add_hol=False, since=2015, include_sat=False
            )

        # Independence Movement Day
        self._add_with_alt_holiday("Independence Movement Day", date(year, MAR, 1))

        # Tree Planting Day
        # removed from holiday since 2006
        if 1949 <= year <= 2005 and year != 1960:
            self._add_holiday("Tree Planting Day", APR, 5)

        # Birthday of the Buddha
        name = "Birthday of the Buddha"
        self._add_with_alt_holiday(
            name, self._add_chinese_birthday_of_buddha(name), add_hol=False, since=2023
        )

        # Children's Day
        if year >= 1975:
            self._add_with_alt_holiday("Children's Day", date(year, MAY, 5), since=2015)

        # Labour Day
        name = "Labour Day"
        if year >= 1994:
            self._add_labor_day(name)
        else:
            self._add_holiday(name, MAR, 10)

        # Memorial Day
        self._add_holiday("Memorial Day", JUN, 6)

        # Constitution Day
        # removed from holiday since 2008
        if year <= 2007:
            self._add_holiday("Constitution Day", JUL, 17)

        # Liberation Day
        self._add_with_alt_holiday("Liberation Day", date(year, AUG, 15))

        # Korean Mid Autumn Day
        name = "Chuseok"
        chuseok_date = self._add_mid_autumn_festival(name)
        self._add_holiday(preceding_day % name, chuseok_date + td(days=-1))
        self._add_holiday(second_day % name, chuseok_date + td(days=+1))

        for delta in (-1, 0, +1):
            self._add_with_alt_holiday(
                name, chuseok_date + td(days=delta), add_hol=False, since=2014, include_sat=False
            )

        # National Foundation Day
        self._add_with_alt_holiday("National Foundation Day", date(year, OCT, 3))

        # Hangeul Day
        if year <= 1990 or year >= 2013:
            self._add_with_alt_holiday("Hangeul Day", date(year, OCT, 9))

        # Christmas Day
        name = "Christmas Day"
        self._add_with_alt_holiday(name, self._add_christmas_day(name), add_hol=False, since=2023)


class Korea(SouthKorea):
    def __init__(self, *args, **kwargs) -> None:
        warnings.warn("Korea is deprecated, use SouthKorea instead.", DeprecationWarning)

        super().__init__(*args, **kwargs)


class KR(SouthKorea):
    pass


class KOR(SouthKorea):
    pass


class SouthKoreaLunisolarCalendar(_CustomChineseCalendar):
    BUDDHA_BIRTHDAY_DATES = {
        1931: (MAY, 25),
        1968: (MAY, 5),
        2001: (MAY, 1),
        2012: (MAY, 28),
        2023: (MAY, 27),
        2025: (MAY, 5),
    }

    LUNAR_NEW_YEAR_DATES = {
        1916: (FEB, 4),
        1944: (JAN, 26),
        1954: (FEB, 4),
        1958: (FEB, 19),
        1966: (JAN, 22),
        1988: (FEB, 18),
        1997: (FEB, 8),
        2027: (FEB, 7),
        2028: (JAN, 27),
    }

    MID_AUTUMN_DATES = {
        1942: (SEP, 25),
        2040: (SEP, 21),
    }
