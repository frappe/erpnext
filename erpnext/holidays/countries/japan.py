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
from gettext import gettext as tr
from typing import Tuple

from holidays.calendars.gregorian import (
    JAN,
    FEB,
    MAR,
    APR,
    MAY,
    JUN,
    JUL,
    AUG,
    SEP,
    OCT,
    NOV,
    DEC,
    MON,
)
from holidays.helpers import _normalize_tuple
from holidays.holiday_base import HolidayBase


class Japan(HolidayBase):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Japan
    """

    country = "JP"
    default_language = "ja"
    special_holidays = {
        1959: (APR, 10, tr("結婚の儀")),  # The Crown Prince marriage ceremony.
        1989: (FEB, 24, tr("大喪の礼")),  # State Funeral of Emperor Shōwa.
        1990: (NOV, 12, tr("即位礼正殿の儀")),  # Enthronement ceremony.
        1993: (JUN, 9, tr("結婚の儀")),  # The Crown Prince marriage ceremony.
        2019: (
            (MAY, 1, tr("天皇の即位の日")),  # Enthronement day.
            (OCT, 22, tr("即位礼正殿の儀が行われる日")),  # Enthronement ceremony.
        ),
    }
    supported_languages = ("en_US", "ja")

    def _populate(self, year):
        if year < 1949 or year > 2099:
            raise NotImplementedError

        super()._populate(year)
        observed_dates = set()

        # New Year's Day.
        observed_dates.add(self._add_holiday(tr("元日"), JAN, 1))

        dt = date(year, JAN, 15) if year <= 1999 else self._get_nth_weekday_of_month(2, MON, JAN)
        # Coming of Age Day.
        observed_dates.add(self._add_holiday(tr("成人の日"), dt))

        if year >= 1967:
            # Foundation Day.
            observed_dates.add(self._add_holiday(tr("建国記念の日"), FEB, 11))

        if year >= 2020:
            # Emperor's Birthday.
            observed_dates.add(self._add_holiday(tr("天皇誕生日"), FEB, 23))

        # Vernal Equinox Day.
        observed_dates.add(self._add_holiday(tr("春分の日"), *self._vernal_equinox_date))

        # Showa Emperor's Birthday, Greenery Day or Showa Day.
        if year <= 1988:
            name = tr("天皇誕生日")
        elif year <= 2006:
            # Greenery Day.
            name = tr("みどりの日")
        else:
            # Showa Day.
            name = tr("昭和の日")
        observed_dates.add(self._add_holiday(name, APR, 29))

        # Constitution Day.
        observed_dates.add(self._add_holiday(tr("憲法記念日"), MAY, 3))

        # Greenery Day.
        if year >= 2007:
            observed_dates.add(self._add_holiday(tr("みどりの日"), MAY, 4))

        # Children's Day.
        observed_dates.add(self._add_holiday(tr("こどもの日"), MAY, 5))

        if year >= 1996:
            if year <= 2002:
                dt = date(year, JUL, 20)
            else:
                dates = {
                    2020: date(2020, JUL, 23),
                    2021: date(2021, JUL, 22),
                }
                dt = dates.get(year, self._get_nth_weekday_of_month(3, MON, JUL))
            # Marine Day.
            observed_dates.add(self._add_holiday(tr("海の日"), dt))

        if year >= 2016:
            dates = {
                2020: date(2020, AUG, 10),
                2021: date(2021, AUG, 8),
            }
            dt = dates.get(year, date(year, AUG, 11))
            # Mountain Day.
            observed_dates.add(self._add_holiday(tr("山の日"), dt))

        if year >= 1966:
            dt = (
                self._get_nth_weekday_of_month(3, MON, SEP)
                if year >= 2003
                else date(year, SEP, 15)
            )
            # Respect for the Aged Day.
            observed_dates.add(self._add_holiday(tr("敬老の日"), dt))

        # Autumnal Equinox Day.
        observed_dates.add(self._add_holiday(tr("秋分の日"), *self._autumnal_equinox_date))

        # Physical Education and Sports Day.
        if year >= 1966:
            name = (
                # Sports Day.
                tr("スポーツの日")
                if year >= 2020
                # Physical Education Day.
                else tr("体育の日")
            )
            dates = {
                2020: date(2020, JUL, 24),
                2021: date(2021, JUL, 23),
            }
            dt = dates.get(
                year,
                self._get_nth_weekday_of_month(2, MON, OCT)
                if year >= 2000
                else date(year, OCT, 10),
            )
            observed_dates.add(self._add_holiday(name, dt))

        # Culture Day.
        observed_dates.add(self._add_holiday(tr("文化の日"), NOV, 3))

        # Labor Thanksgiving Day.
        observed_dates.add(self._add_holiday(tr("勤労感謝の日"), NOV, 23))

        # Regarding the Emperor of Heisei.
        if 1989 <= year <= 2018:
            observed_dates.add(self._add_holiday(tr("天皇誕生日"), DEC, 23))

        if self.observed:
            for month, day, _ in _normalize_tuple(self.special_holidays.get(year, ())):
                observed_dates.add(date(year, month, day))

            # When a national holiday falls on Sunday, next working day
            # shall become a public holiday (振替休日) - substitute holidays.
            for dt in observed_dates.copy():
                if not self._is_sunday(dt):
                    continue
                hol_date = dt + td(days=+1)
                while hol_date in observed_dates:
                    hol_date += td(days=+1)
                # Substitute Holiday.
                observed_dates.add(self._add_holiday(tr("振替休日"), hol_date))

            # A weekday between national holidays becomes
            # a holiday too (国民の休日) - citizens' holidays.
            for dt in observed_dates:
                if dt + td(days=+2) not in observed_dates:
                    continue
                hol_date = dt + td(days=+1)
                if self._is_sunday(hol_date) or hol_date in observed_dates:
                    continue
                # National Holiday.
                self._add_holiday(tr("国民の休日"), hol_date)

    @property
    def _vernal_equinox_date(self) -> Tuple[int, int]:
        day = 20
        if (
            (self._year % 4 == 0 and self._year <= 1956)
            or (self._year % 4 == 1 and self._year <= 1989)
            or (self._year % 4 == 2 and self._year <= 2022)
            or (self._year % 4 == 3 and self._year <= 2055)
        ):
            day = 21
        elif self._year % 4 == 0 and self._year >= 2092:
            day = 19
        return MAR, day

    @property
    def _autumnal_equinox_date(self) -> Tuple[int, int]:
        day = 23
        if self._year % 4 == 3 and self._year <= 1979:
            day = 24
        elif (
            (self._year % 4 == 0 and self._year >= 2012)
            or (self._year % 4 == 1 and self._year >= 2045)
            or (self._year % 4 == 2 and self._year >= 2078)
        ):
            day = 22
        return SEP, day


class JP(Japan):
    pass


class JPN(Japan):
    pass
