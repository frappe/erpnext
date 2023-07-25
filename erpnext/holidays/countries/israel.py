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

from holidays.calendars import _HebrewLunisolar
from holidays.holiday_base import HolidayBase


class Israel(HolidayBase):
    country = "IL"

    def _add_with_eve(self, name: str, dt: date) -> None:
        self._add_holiday(f"{name} - Eve", dt + td(days=-1))
        self._add_holiday(name, dt)

    def _populate(self, year):
        if year <= 1947:
            return None

        if year >= 2101:
            raise NotImplementedError

        super()._populate(year)

        # Passover
        passover_dt = _HebrewLunisolar.hebrew_holiday_date(year, "PASSOVER")
        self._add_with_eve("Passover I", passover_dt)
        for offset in range(1, 5):
            self._add_holiday("Passover - Chol HaMoed", passover_dt + td(days=offset))
        self._add_with_eve("Passover VII", passover_dt + td(days=+6))

        # Memorial Day
        memorial_day_dt = _HebrewLunisolar.hebrew_holiday_date(year, "MEMORIAL_DAY")
        observed_delta = 0
        if self.observed:
            if self._is_thursday(memorial_day_dt):
                observed_delta = -1
            elif self._is_friday(memorial_day_dt):
                observed_delta = -2
            elif year >= 2004 and self._is_sunday(memorial_day_dt):
                observed_delta = 1

        name = "Memorial Day"
        if observed_delta != 0:
            self._add_holiday(f"{name} (Observed)", memorial_day_dt + td(days=observed_delta))
        else:
            self._add_holiday(name, memorial_day_dt)

        # Independence Day
        name = "Independence Day"
        if self.observed and observed_delta != 0:
            self._add_holiday(f"{name} (Observed)", memorial_day_dt + td(days=observed_delta + 1))
        else:
            self._add_holiday(name, memorial_day_dt + td(days=+1))

        # Lag Baomer
        lag_baomer_dt = _HebrewLunisolar.hebrew_holiday_date(year, "LAG_BAOMER")
        self._add_holiday("Lag B'Omer", lag_baomer_dt)

        # Shavuot
        shavuot_dt = _HebrewLunisolar.hebrew_holiday_date(year, "SHAVUOT")
        self._add_with_eve("Shavuot", shavuot_dt)

        # Rosh Hashana
        rosh_hashanah_dt = _HebrewLunisolar.hebrew_holiday_date(year, "ROSH_HASHANAH")
        name = "Rosh Hashanah"
        self._add_with_eve(name, rosh_hashanah_dt)
        self._add_holiday(name, rosh_hashanah_dt + td(days=+1))

        # Yom Kippur
        yom_kippur_dt = _HebrewLunisolar.hebrew_holiday_date(year, "YOM_KIPPUR")
        self._add_with_eve("Yom Kippur", yom_kippur_dt)

        # Sukkot
        sukkot_dt = _HebrewLunisolar.hebrew_holiday_date(year, "SUKKOT")
        self._add_with_eve("Sukkot I", sukkot_dt)
        for offset in range(1, 6):
            self._add_holiday("Sukkot - Chol HaMoed", sukkot_dt + td(days=offset))
        self._add_with_eve("Sukkot VII", sukkot_dt + td(days=+7))

        # Hanukkah
        # Some o prior's year Hannukah may fall in current year.
        for yr in (year - 1, year):
            hanukkah_dt = _HebrewLunisolar.hebrew_holiday_date(yr, "HANUKKAH")
            for offset in range(8):
                self._add_holiday("Hanukkah", hanukkah_dt + td(days=offset))

        # Purim
        purim_dt = _HebrewLunisolar.hebrew_holiday_date(year, "PURIM")
        self._add_with_eve("Purim", purim_dt)
        self._add_holiday("Shushan Purim", purim_dt + td(days=+1))


class IL(Israel):
    pass


class ISR(Israel):
    pass
