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
#  Copyright: Kateryna Golovanova <kate@kgthreads.com>, 2022

from datetime import timedelta as td

from holidays.calendars.gregorian import JAN, APR, MAY, JUN, JUL, AUG, SEP, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Bolivia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Bolivia
    https://www.officeholidays.com/countries/bolivia
    """

    country = "BO"
    subdivisions = (
        "B",
        "C",
        "H",
        "L",
        "N",
        "O",
        "P",
        "S",
        "T",
    )

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)
        observed_dates = set()

        # New Year's Day.
        if year >= 1825:
            observed_dates.add(self._add_new_years_day("Año Nuevo"))

        # Plurinational State Foundation Day.
        if year >= 2010:
            self._add_holiday("Nacimiento del Estado Plurinacional de Bolivia", JAN, 22)

        # Carnival.
        name = "Feriado por Carnaval"
        self._add_carnival_monday(name)
        self._add_carnival_tuesday(name)

        # Good Friday.
        self._add_good_friday("Viernes Santo")

        # Labor Day.
        observed_dates.add(self._add_labor_day("Día del trabajo"))

        # Corpus Christi.
        self._add_corpus_christi_day("Corpus Christi")

        if year >= 2010:
            # Andean New Year.
            observed_dates.add(self._add_holiday("Año Nuevo Andino", JUN, 21))

        if year >= 1825:
            # Independence Day.
            observed_dates.add(self._add_holiday("Día de la Patria", AUG, 6))

        # All Soul's Day.
        observed_dates.add(self._add_all_souls_day("Todos Santos"))

        # Christmas Day.
        observed_dates.add(self._add_christmas_day("Navidad"))

        if self.observed:
            for dt in sorted(observed_dates):
                if not self._is_sunday(dt):
                    continue
                self._add_holiday(f"{self[dt]} (Observed)", dt + td(days=+1))

    def _add_subdiv_b_holidays(self):
        # Beni Day.
        self._add_holiday("Día del departamento de Beni", NOV, 18)

    def _add_subdiv_c_holidays(self):
        # Cochabamba Day.
        self._add_holiday("Día del departamento de Cochabamba", SEP, 14)

    def _add_subdiv_h_holidays(self):
        # Chuquisaca Day.
        self._add_holiday("Día del departamento de Chuquisaca", MAY, 25)

    def _add_subdiv_l_holidays(self):
        # La Paz Day.
        self._add_holiday("Día del departamento de La Paz", JUL, 16)

    def _add_subdiv_n_holidays(self):
        # Pando Day.
        self._add_holiday("Día del departamento de Pando", SEP, 24)

    def _add_subdiv_p_holidays(self):
        # Potosí Day.
        self._add_holiday("Día del departamento de Potosí", NOV, 10)

    def _add_subdiv_o_holidays(self):
        # Carnival in Oruro.
        self._add_holiday("Carnaval de Oruro", self._easter_sunday + td(days=-51))

    def _add_subdiv_s_holidays(self):
        # Santa Cruz Day.
        self._add_holiday("Día del departamento de Santa Cruz", SEP, 24)

    def _add_subdiv_t_holidays(self):
        # La Tablada.
        self._add_holiday("La Tablada", APR, 15)


class BO(Bolivia):
    pass


class BOL(Bolivia):
    pass
