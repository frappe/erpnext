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

from holidays.calendars.gregorian import JUN, SEP, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Guatemala(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - http://www.bvnsa.com.gt/bvnsa/calendario_dias_festivos.php
    - https://www.minfin.gob.gt/images/downloads/leyes_acuerdos/decretocong19_101018.pdf
    """

    country = "GT"
    default_language = "es"
    supported_languages = ("en_US", "es")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _move_holiday(self, dt: date) -> None:
        """
        law 19-2018 start 18 oct 2018
        https://www.minfin.gob.gt/images/downloads/leyes_acuerdos/decretocong19_101018.pdf


        EXPEDIENTE 5536-2018 (CC) start 17 abr 2020
        https://leyes.infile.com/index.php?id=181&id_publicacion=81051
        """
        if dt <= date(2018, OCT, 17) or self._is_monday(dt):
            return None
        self._add_holiday(
            self[dt],
            self._get_nth_weekday_from(-1, MON, dt)
            if self._is_tuesday(dt) or self._is_wednesday(dt)
            else self._get_nth_weekday_from(1, MON, dt),
        )
        self.pop(dt)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Good Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Good Saturday.
        self._add_holy_saturday(tr("Sabado Santo"))

        # Labor Day.
        dt = self._add_labor_day(tr("Dia del Trabajo"))
        if year == 2019:
            self._move_holiday(dt)

        # Army Day.
        self._move_holiday(self._add_holiday(tr("Dia del Ejército"), JUN, 30))

        # Assumption Day.
        self._add_assumption_of_mary_day(tr("Dia de la Asunción"))

        # Independence Day
        self._add_holiday(tr("Día de la Independencia"), SEP, 15)

        # Revolution Day
        dt = self._add_holiday(tr("Dia de la Revolución"), OCT, 20)
        if year in {2018, 2019}:
            self._move_holiday(dt)

        # All Saints' Day.
        self._add_all_saints_day(tr("Dia de Todos los Santos"))

        # Christmas Day.
        self._add_christmas_day(tr("Dia de Navidad"))


class GT(Guatemala):
    pass


class GUA(Guatemala):
    pass
