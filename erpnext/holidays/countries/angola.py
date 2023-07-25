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

from holidays.calendars.gregorian import FEB, MAR, APR, SEP, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Angola(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.officeholidays.com/countries/angola/
    https://www.timeanddate.com/holidays/angola/
    """

    country = "AO"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed_holiday(self, dt, before: bool = True) -> None:
        # As of 1995/1/1, whenever a public holiday falls on a Sunday,
        # it rolls over to the following Monday
        # Since 2018 when a public holiday falls on the Tuesday or Thursday
        # the Monday or Friday is also a holiday
        if self.observed and self._year >= 1995:
            for name in self.get_list(dt):
                if self._year <= 2017:
                    if self._is_sunday(dt):
                        self._add_holiday("%s (Observed)" % name, dt + td(days=+1))
                else:
                    if self._is_tuesday(dt) and before:
                        self._add_holiday("%s (Day off)" % name, dt + td(days=-1))
                    elif self._is_thursday(dt):
                        self._add_holiday("%s (Day off)" % name, dt + td(days=+1))

    def _populate(self, year: int) -> None:
        # Observed since 1975
        # TODO do more research on history of Angolan holidays
        if year <= 1974:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_observed_holiday(self._add_new_years_day("Ano novo"), before=False)
        # Since 2018, if the following year's New Year's Day falls on a
        # Tuesday, the 31st of the current year is also a holiday.
        if self.observed and self._is_monday(DEC, 31) and year >= 2018:
            self._add_holiday("Ano novo (Day off)", DEC, 31)

        # Good Friday.
        self._add_good_friday("Sexta-feira Santa")

        # Carnival.
        self._add_observed_holiday(self._add_carnival_tuesday("Carnaval"))

        # Liberation Movement Day.
        self._add_observed_holiday(self._add_holiday("Dia do Início da Luta Armada", FEB, 4))

        # Day off for International Woman's Day.
        self._add_observed_holiday(self._add_womens_day("Dia Internacional da Mulher"))

        # Southern Africa Liberation Day.
        if year >= 2019:
            self._add_observed_holiday(
                self._add_holiday("Dia da Libertação da África Austral", MAR, 23)
            )

        # Peace Day.
        self._add_observed_holiday(self._add_holiday("Dia da Paz e Reconciliação", APR, 4))

        # May Day.
        self._add_observed_holiday(self._add_labor_day("Dia Mundial do Trabalho"))

        # National Hero Day.
        if year >= 1980:
            self._add_observed_holiday(self._add_holiday("Dia do Herói Nacional", SEP, 17))

        # All Souls' Day.
        self._add_observed_holiday(self._add_all_souls_day("Dia dos Finados"))

        # Independence Day.
        self._add_observed_holiday(self._add_holiday("Dia da Independência", NOV, 11))

        # Christmas Day.
        self._add_observed_holiday(self._add_christmas_day("Dia de Natal e da Família"))


class AO(Angola):
    pass


class AGO(Angola):
    pass
