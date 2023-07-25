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
from gettext import gettext as tr

from holidays.calendars.gregorian import APR, JUL, AUG, SEP, DEC, MON, SUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class CostaRica(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Costa_Rica
    - Law #8442 from 19.04.2005
    - Law #8604 from 17.09.2007
    - Law #8753 from 25.07.2009
    - Law #8886 from 01.11.2010
    - Law #9803 from 19.05.2020
    - Law #10050 from 25.10.2021
    """

    country = "CR"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _move_holiday(self, dt: date, forward: bool = False) -> None:
        if not self.observed or self._is_monday(dt) or (forward and self._is_weekend(dt)):
            return None
        obs_dt = (
            self._get_nth_weekday_from(1, MON, dt)
            if forward or not (self._is_tuesday(dt) or self._is_wednesday(dt))
            else self._get_nth_weekday_from(-1, MON, dt)
        )
        self._add_holiday(self.tr("%s (Observado)") % self[dt], obs_dt)
        self.pop(dt)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Maundy Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Juan Santamaría Day.
        dt = self._add_holiday(tr("Día de Juan Santamaría"), APR, 11)
        if 2006 <= year <= 2010:
            self._move_holiday(dt, forward=True)
        elif year in {2023, 2024}:
            self._move_holiday(dt)

        # International Labor Day.
        dt = self._add_labor_day(tr("Día Internacional del Trabajo"))
        if year == 2021:
            self._move_holiday(dt)

        # Annexation of the Party of Nicoya to Costa Rica.
        dt = self._add_holiday(tr("Anexión del Partido de Nicoya a Costa Rica"), JUL, 25)
        if 2005 <= year <= 2008:
            self._move_holiday(dt, forward=True)
        elif 2020 <= year <= 2024:
            self._move_holiday(dt)

        # Feast of Our Lady of the Angels.
        self._add_holiday(tr("Fiesta de Nuestra Señora de los Ángeles"), AUG, 2)

        # Mother's Day.
        dt = self._add_assumption_of_mary_day(tr("Día de la Madre"))
        if 2005 <= year <= 2007:
            self._move_holiday(dt, forward=True)
        elif year in {2020, 2023, 2024}:
            self._move_holiday(dt)

        if year >= 2022:
            dt = date(year, AUG, 31)
            # Day of the Black Person and Afro-Costa Rican Culture.
            name = self.tr("Día de la Persona Negra y la Cultura Afrocostarricense")
            if self.observed and year in {2022, 2023}:
                dt = self._get_nth_weekday_from(1, SUN, dt)
                name = self.tr("%s (Observado)") % name
            self._add_holiday(name, dt)

        # Independence Day.
        dt = self._add_holiday(tr("Día de la Independencia"), SEP, 15)
        if year in {2020, 2021, 2022, 2024}:
            self._move_holiday(dt)

        if year <= 2019:
            # Cultures Day.
            self._move_holiday(self._add_columbus_day(tr("Día de las Culturas")), forward=True)

        if year >= 2020:
            # Army Abolition Day.
            dt = self._add_holiday(tr("Día de la Abolición del Ejército"), DEC, 1)
            if year in {2020, 2021, 2022}:
                self._move_holiday(dt)

        # Christmas Day.
        self._add_christmas_day(tr("Navidad"))


class CR(CostaRica):
    pass


class CRI(CostaRica):
    pass
