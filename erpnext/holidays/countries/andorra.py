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

from holidays.calendars.gregorian import MAR, JUL, AUG, SEP, FRI, SAT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Andorra(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Andorra
      - https://www.holsdb.com/public-holidays/ad
    """

    country = "AD"
    subdivisions = (
        "02",  # Canillo.
        "03",  # Encamp.
        "04",  # La Massana.
        "05",  # Ordino.
        "06",  # Sant Julià de Lòria.
        "07",  # Andorra la Vella.
        "08",  # Escaldes-Engordany.
    )

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year: int) -> None:
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Epiphany.
        self._add_epiphany_day("Epiphany")

        # Carnival.
        self._add_carnival_tuesday("Carnival")

        # Constitution Day.
        self._add_holiday("Constitution Day", MAR, 14)

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Easter Sunday.
        self._add_easter_monday("Easter Monday")

        # Labor Day.
        self._add_labor_day("Labor Day")

        # Whit Monday.
        self._add_whit_monday("Whit Monday")

        # Assumption Day.
        self._add_assumption_of_mary_day("Assumption Day")

        # National Day.
        self._add_holiday("National Day", SEP, 8)

        # All Saints' Day.
        self._add_all_saints_day("All Saints' Day")

        # Immaculate Conception Day.
        self._add_immaculate_conception_day("Immaculate Conception Day")

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Saint Stephen's Day.
        self._add_christmas_day_two("Saint Stephen's Day")

    # Canillo.
    def _add_subdiv_02_holidays(self):
        name = "Canillo Annual Festival"
        third_sat_of_july = self._get_nth_weekday_of_month(3, SAT, JUL)
        self._add_holiday(name, third_sat_of_july)
        self._add_holiday(name, third_sat_of_july + td(days=+1))
        self._add_holiday(name, third_sat_of_july + td(days=+2))

    # Encamp.
    def _add_subdiv_03_holidays(self):
        name = "Encamp Annual Festival"
        aug_15 = self._add_holiday(name, AUG, 15)
        self._add_holiday(name, aug_15 + td(days=+1))

    # La Massana.
    def _add_subdiv_04_holidays(self):
        name = "La Massana Annual Festival"
        aug_15 = self._add_holiday(name, AUG, 15)
        self._add_holiday(name, aug_15 + td(days=+1))

    # Ordino.
    def _add_subdiv_05_holidays(self):
        name = "Ordino Annual Festival"
        aug_15 = self._add_holiday(name, AUG, 15)
        self._add_holiday(name, aug_15 + td(days=+1))

    # Sant Julià de Lòria.
    def _add_subdiv_06_holidays(self):
        name = "Sant Julià de Lòria Annual Festival"
        last_fri_of_july = self._get_nth_weekday_from(-1, FRI, JUL, 29)
        self._add_holiday(name, last_fri_of_july)
        self._add_holiday(name, last_fri_of_july + td(days=+1))
        self._add_holiday(name, last_fri_of_july + td(days=+2))
        self._add_holiday(name, last_fri_of_july + td(days=+3))

    # Andorra la Vella.
    def _add_subdiv_07_holidays(self):
        name = "Andorra la Vella Annual Festival"
        first_sat_of_august = self._get_nth_weekday_of_month(1, SAT, AUG)
        self._add_holiday(name, first_sat_of_august)
        self._add_holiday(name, first_sat_of_august + td(days=+1))
        self._add_holiday(name, first_sat_of_august + td(days=+2))

    # Escaldes-Engordany.
    def _add_subdiv_08_holidays(self):
        name = "Escaldes-Engordany Annual Festival"
        jul_25 = self._add_holiday(name, JUL, 25)
        self._add_holiday(name, jul_25 + td(days=+1))


class AD(Andorra):
    pass


class AND(Andorra):
    pass
