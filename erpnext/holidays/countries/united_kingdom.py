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
from typing import Tuple, Union

from holidays.calendars.gregorian import MAR, APR, MAY, JUN, JUL, AUG, SEP, NOV, DEC, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class UnitedKingdom(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_the_United_Kingdom
    """

    country = "GB"
    special_holidays = {
        1977: (JUN, 7, "Silver Jubilee of Elizabeth II"),
        1981: (JUL, 29, "Wedding of Charles and Diana"),
        1999: (DEC, 31, "Millennium Celebrations"),
        2002: (JUN, 3, "Golden Jubilee of Elizabeth II"),
        2011: (APR, 29, "Wedding of William and Catherine"),
        2012: (JUN, 5, "Diamond Jubilee of Elizabeth II"),
        2022: (
            (JUN, 3, "Platinum Jubilee of Elizabeth II"),
            (SEP, 19, "State Funeral of Queen Elizabeth II"),
        ),
        2023: (MAY, 8, "Coronation of Charles III"),
    }
    subdivisions: Union[Tuple[()], Tuple[str, ...]] = (
        "ENG",  # England
        "NIR",  # Northern Ireland
        "SCT",  # Scotland
        "WLS",  # Wales
    )
    _deprecated_subdivisions: Tuple[str, ...] = (
        "England",
        "Northern Ireland",
        "Scotland",
        "UK",
        "Wales",
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_weekend(dt):
            self._add_holiday(
                "%s (Observed)" % self[dt], dt + td(days=+2 if self._is_saturday(dt) else days)
            )

    def _populate(self, year: int) -> None:
        super()._populate(year)

        # Good Friday
        self._add_good_friday("Good Friday")

        # May Day bank holiday (first Monday in May)
        if year >= 1978:
            dt = (
                date(year, MAY, 8)
                # In 2020 moved to Friday to mark 75th anniversary of VE Day.
                if year in {1995, 2020}
                else self._get_nth_weekday_of_month(1, MON, MAY)
            )
            self._add_holiday("May Day", dt)

        # Spring bank holiday (last Monday in May)
        if year >= 1971:
            spring_bank_dates = {
                2002: date(year, JUN, 4),
                2012: date(year, JUN, 4),
                2022: date(year, JUN, 2),
            }
            dt = spring_bank_dates.get(year, self._get_nth_weekday_of_month(-1, MON, MAY))
            self._add_holiday("Spring Bank Holiday", dt)

        if self.subdiv == "England":
            self._add_subdiv_eng_holidays()
        elif self.subdiv == "Northern Ireland":
            self._add_subdiv_nir_holidays()
        elif self.subdiv == "Scotland":
            self._add_subdiv_sct_holidays()
        elif self.subdiv == "Wales":
            self._add_subdiv_wls_holidays()

    def _add_subdiv_holidays(self):
        if self.subdiv not in {"SCT", "Scotland"}:
            # New Year's Day
            if self._year >= 1975:
                self._add_observed(self._add_new_years_day("New Year's Day"))

            # Christmas Day
            self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)

            # Boxing Day
            self._add_observed(self._add_christmas_day_two("Boxing Day"), days=+2)

        super()._add_subdiv_holidays()

    def _add_subdiv_eng_holidays(self):
        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # Late Summer bank holiday (last Monday in August)
        if self._year >= 1971:
            self._add_holiday(
                "Late Summer Bank Holiday", self._get_nth_weekday_of_month(-1, MON, AUG)
            )

    def _add_subdiv_nir_holidays(self):
        if self._year >= 1903:
            # St. Patrick's Day
            self._add_observed(self._add_holiday("St. Patrick's Day", MAR, 17))

        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # Battle of the Boyne
        self._add_holiday("Battle of the Boyne", JUL, 12)

        # Late Summer bank holiday (last Monday in August)
        if self._year >= 1971:
            self._add_holiday(
                "Late Summer Bank Holiday", self._get_nth_weekday_of_month(-1, MON, AUG)
            )

    def _add_subdiv_sct_holidays(self):
        # New Year's Day
        name = "New Year's Day"
        jan_1 = self._add_new_years_day(name)
        if self.observed and self._is_weekend(jan_1):
            self._add_holiday(
                "%s (Observed)" % name, jan_1 + td(days=+3 if self._is_saturday(jan_1) else +1)
            )

        # New Year Holiday
        name = "New Year Holiday"
        jan_2 = self._add_new_years_day_two(name)
        self._add_observed(jan_2)
        if self.observed and self._is_monday(jan_2):
            self._add_new_years_day_three("%s (Observed)" % name)

        # Summer bank holiday (first Monday in August)
        self._add_holiday("Summer Bank Holiday", self._get_nth_weekday_of_month(1, MON, AUG))

        if self._year >= 2006:
            # St. Andrew's Day
            self._add_holiday("St. Andrew's Day", NOV, 30)

        # Christmas Day
        self._add_observed(
            self._add_christmas_day("Christmas Day"), days=+2 if self._year >= 1974 else +1
        )

        if self._year >= 1974:
            # Boxing Day
            self._add_observed(self._add_christmas_day_two("Boxing Day"), days=+2)

    def _add_subdiv_wls_holidays(self):
        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # Late Summer bank holiday (last Monday in August)
        if self._year >= 1971:
            self._add_holiday(
                "Late Summer Bank Holiday", self._get_nth_weekday_of_month(-1, MON, AUG)
            )


class UK(UnitedKingdom):
    pass


class GB(UnitedKingdom):
    pass


class GBR(UnitedKingdom):
    pass
