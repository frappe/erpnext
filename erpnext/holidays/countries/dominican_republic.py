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

from holidays.calendars.gregorian import JAN, FEB, JUN, AUG, SEP, NOV, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class DominicanRepublic(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    http://ojd.org.do/Normativas/LABORAL/Leyes/Ley%20No.%20%20139-97.pdf
    https://es.wikipedia.org/wiki/Rep%C3%BAblica_Dominicana#D%C3%ADas_festivos_nacionales
    """

    country = "DO"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def _move_holiday(self, dt: date, include_sun: bool = False) -> None:
        # Law No. 139-97 - Holidays Dominican Republic - Jun 27, 1997
        if dt < date(1997, JUN, 27):
            return None
        obs_dt = None
        if self._is_tuesday(dt) or self._is_wednesday(dt):
            obs_dt = self._get_nth_weekday_from(-1, MON, dt)
        elif self._is_thursday(dt) or self._is_friday(dt) or (include_sun and self._is_sunday(dt)):
            obs_dt = self._get_nth_weekday_from(1, MON, dt)
        if obs_dt:
            self._add_holiday(self[dt], obs_dt)
            self.pop(dt)

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Epiphany.
        self._move_holiday(self._add_epiphany_day(tr("Día de los Santos Reyes")))

        # Lady of Altagracia.
        self._add_holiday(tr("Día de la Altagracia"), JAN, 21)

        # Juan Pablo Duarte Day.
        self._move_holiday(self._add_holiday(tr("Día de Duarte"), JAN, 26))

        # Independence Day.
        self._add_holiday(tr("Día de Independencia"), FEB, 27)

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Labor Day.
        self._move_holiday(self._add_labor_day(tr("Día del Trabajo")), include_sun=True)

        # Feast of Corpus Christi.
        self._add_corpus_christi_day(tr("Corpus Christi"))

        # Restoration Day.
        name = tr("Día de la Restauración")
        # Judgment No. 14 of Feb 20, 2008 of the Supreme Court of Justice
        if year <= 2007 and year % 4 == 0:
            self._add_holiday(name, AUG, 16)
        else:
            self._move_holiday(self._add_holiday(name, AUG, 16))

        # Our Lady of Mercedes Day.
        self._add_holiday(tr("Día de las Mercedes"), SEP, 24)

        # Constitution Day.
        self._move_holiday(self._add_holiday(tr("Día de la Constitución"), NOV, 6))

        # Christmas Day.
        self._add_christmas_day(tr("Día de Navidad"))


class DO(DominicanRepublic):
    pass


class DOM(DominicanRepublic):
    pass
