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

from holidays.calendars.gregorian import FEB, APR, MAY, JUN, SEP, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Mozambique(HolidayBase, ChristianHolidays, InternationalHolidays):
    country = "MZ"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        # whenever a public holiday falls on a Sunday,
        # it rolls over to the following Monday
        if self.observed and self._is_sunday(dt):
            self._add_holiday("%s (PONTE)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        if year <= 1974:
            return None

        super()._populate(year)

        self._add_observed(self._add_new_years_day("Ano novo"))

        self._add_good_friday("Sexta-feira Santa")

        self._add_carnival_tuesday("Carnaval")

        self._add_observed(self._add_holiday("Dia dos Heróis Moçambicanos", FEB, 3))

        self._add_observed(self._add_holiday("Dia da Mulher Moçambicana", APR, 7))

        self._add_observed(self._add_holiday("Dia Mundial do Trabalho", MAY, 1))

        self._add_observed(self._add_holiday("Dia da Independência Nacional", JUN, 25))

        self._add_observed(self._add_holiday("Dia da Vitória", SEP, 7))

        self._add_observed(self._add_holiday("Dia das Forças Armadas", SEP, 25))

        if year >= 1993:
            self._add_observed(self._add_holiday("Dia da Paz e Reconciliação", OCT, 4))

        self._add_observed(self._add_christmas_day("Dia de Natal e da Família"))


class MZ(Mozambique):
    pass


class MOZ(Mozambique):
    pass
