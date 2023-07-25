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
from typing import Optional

from holidays.calendars.gregorian import JUN, JUL, AUG, SEP, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import (
    ChineseCalendarHolidays,
    ChristianHolidays,
    InternationalHolidays,
)


class HongKong(HolidayBase, ChineseCalendarHolidays, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Hong_Kong
    Holidays for 2007–2023 (government source):
    https://www.gov.hk/en/about/abouthk/holiday/index.htm
    """

    country = "HK"
    special_holidays = {
        1997: (JUL, 2, "Hong Kong Special Administrative Region Establishment Day"),
        2015: (
            (
                SEP,
                3,
                "The 70th anniversary day of the victory of the Chinese "
                "people's war of resistance against Japanese aggression",
            )
        ),
    }

    def __init__(self, *args, **kwargs):
        ChineseCalendarHolidays.__init__(self)
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_holiday(self, *args) -> Optional[date]:
        name, dt = self._parse_holiday(*args)
        if self.observed and (self._is_sunday(dt) or dt in self):
            while self._is_sunday(dt) or dt in self:
                dt += td(days=+1)
            name = self.tr("The day following %s") % self.tr(name)
        self[dt] = self.tr(name)
        return dt

    def _populate(self, year):
        # Current set of holidays actually valid since 1946
        if year <= 1945:
            return None

        super()._populate(year)

        day_following = "The day following "

        # The first day of January
        self._add_new_years_day("The first day of January")

        # Lunar New Year
        name = "Lunar New Year's Day"
        preceding_day_lunar = "The day preceding Lunar New Year's Day"
        second_day_lunar = "The second day of Lunar New Year"
        third_day_lunar = "The third day of Lunar New Year"
        fourth_day_lunar = "The fourth day of Lunar New Year"
        new_year_date = self._chinese_new_year
        if self.observed:
            if self._is_sunday(new_year_date):
                if year in {2006, 2007, 2010}:
                    self._add_chinese_new_years_eve(preceding_day_lunar)
                else:
                    self._add_chinese_new_years_day_four(fourth_day_lunar)
            else:
                self._add_chinese_new_years_day(name)
            if self._is_saturday(new_year_date):
                self._add_chinese_new_years_day_four(fourth_day_lunar)
            else:
                self._add_chinese_new_years_day_two(second_day_lunar)
            if self._is_friday(new_year_date):
                self._add_chinese_new_years_day_four(fourth_day_lunar)
            else:
                self._add_chinese_new_years_day_three(third_day_lunar)
        else:
            self._add_chinese_new_years_day(name)
            self._add_chinese_new_years_day_two(second_day_lunar)
            self._add_chinese_new_years_day_three(third_day_lunar)

        easter_monday_date = self._easter_sunday + td(days=+1)

        # Ching Ming Festival
        name = "Ching Ming Festival"
        ching_ming_date = self._qingming_date
        if self.observed and ching_ming_date == easter_monday_date:
            self._add_holiday(f"{day_following}{name}", ching_ming_date + td(days=+1))
        elif ching_ming_date not in {
            self._easter_sunday + td(days=-2),
            self._easter_sunday + td(days=-1),
        }:
            self._add_holiday(name, ching_ming_date)

        # Easter Holiday
        good_friday = "Good Friday"
        easter_monday = "Easter Monday"
        self._add_good_friday(good_friday)
        self._add_holy_saturday(f"{day_following}{good_friday}")
        self._add_easter_monday(easter_monday)

        if ching_ming_date in {
            self._easter_sunday + td(days=-2),
            self._easter_sunday + td(days=-1),
        }:
            super()._add_holiday(name, ching_ming_date)

        if year >= 1999:
            # The Birthday of the Buddha
            self._add_chinese_birthday_of_buddha("The Birthday of the Buddha")

            # Labour Day
            self._add_labor_day("Labour Day")

        # Tuen Ng Festival
        self._add_dragon_boat_festival("Tuen Ng Festival")

        # Hong Kong Special Administrative Region Establishment Day
        if year >= 1997:
            self._add_holiday("Hong Kong Special Administrative Region Establishment Day", JUL, 1)

        # Chinese Mid-Autumn Festival
        name = "Chinese Mid-Autumn Festival"
        mid_autumn_date = self._mid_autumn_festival
        if self.observed:
            # if Chinese Mid-Autumn Festival lies on Saturday
            # before 1983 public holiday lies on Monday
            # from 1983 to 2010 public holiday lies on same day
            # since 2011 public holiday lies on Monday
            if self._is_saturday(mid_autumn_date):
                if 1983 <= year <= 2010:
                    self._add_mid_autumn_festival(name)
                else:
                    self._add_holiday(
                        f"The second day of the {name} (Monday)", mid_autumn_date + td(days=+2)
                    )
            else:
                self._add_mid_autumn_festival_day_two(f"The day following the {name}")
        else:
            self._add_mid_autumn_festival_day_two(name)

        # Chung Yeung Festival
        self._add_double_ninth_festival("Chung Yeung Festival")

        # National Day
        if year >= 1997:
            self._add_holiday("National Day", OCT, 1)

            if year <= 1998:
                self._add_holiday("National Day", OCT, 2)

        # Christmas Day
        name = "Christmas Day"
        first_after_christmas = f"The first weekday after {name}"
        second_after_christmas = f"The second weekday after {name}"
        christmas_date = self._christmas_day
        if self.observed:
            if self._is_sunday(christmas_date):
                self._add_christmas_day_two(first_after_christmas)
                self._add_christmas_day_three(second_after_christmas)
            elif self._is_saturday(christmas_date):
                self._add_christmas_day(name)
                self._add_christmas_day_three(first_after_christmas)
            else:
                self._add_christmas_day(name)
                self._add_christmas_day_two(first_after_christmas)
        else:
            self._add_christmas_day(name)
            self._add_christmas_day_two(first_after_christmas)

        # Previous holidays
        if 1952 <= year <= 1997:
            # Queen's Birthday (June 2nd Monday)
            self._add_holiday("Queen's Birthday", self._get_nth_weekday_of_month(2, MON, JUN))

        if year <= 1996:
            # Anniversary of the liberation of Hong Kong (August last Monday)
            self._add_holiday(
                "Anniversary of the liberation of Hong Kong",
                self._get_nth_weekday_of_month(-1, MON, AUG),
            )

        if year <= 1998:
            # Anniversary of the victory in the Second Sino-Japanese War
            super()._add_holiday(
                "Anniversary of the victory in the Second Sino-Japanese War",
                self._get_nth_weekday_of_month(-1, MON, AUG) + td(days=-1),
            )


class HK(HongKong):
    pass


class HKG(HongKong):
    pass
