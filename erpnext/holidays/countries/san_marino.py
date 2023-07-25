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

from holidays.calendars.gregorian import FEB, MAR, JUL, SEP
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class SanMarino(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_San_Marino
    """

    country = "SM"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year: int) -> None:
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Epiphany.
        self._add_epiphany_day("Epiphany")

        # Feast of Saint Agatha.
        self._add_holiday("Feast of Saint Agatha", FEB, 5)

        # Anniversary of the Arengo.
        self._add_holiday("Anniversary of the Arengo", MAR, 25)

        # Easter Sunday.
        self._add_easter_sunday("Easter Sunday")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # Labour Day.
        self._add_labor_day("Labour Day")

        # Corpus Cristi.
        self._add_corpus_christi_day("Corpus Cristi")

        # Liberation from Fascism Day.
        self._add_holiday("Liberation from Fascism Day", JUL, 28)

        # Assumption of Mary.
        self._add_assumption_of_mary_day("Assumption Day")

        # The Feast of Saint Marinus and the Republic.
        self._add_holiday("Foundation Day", SEP, 3)

        # All Saints' Day.
        self._add_all_saints_day("All Saints' Day")

        # Commemoration of the Dead.
        self._add_all_souls_day("Commemoration of the Dead")

        # Immaculate Conception.
        self._add_immaculate_conception_day("Immaculate Conception Day")

        # Christmas Eve.
        self._add_christmas_eve("Christmas Eve")

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Saint Stephen's Day.
        self._add_christmas_day_two("Saint Stephen's Day")

        # New Year's Eve.
        self._add_new_years_eve("New Year's Eve")


class SM(SanMarino):
    pass


class SMR(SanMarino):
    pass
