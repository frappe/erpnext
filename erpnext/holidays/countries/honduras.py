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
from gettext import gettext as tr

from holidays.calendars.gregorian import APR, SEP, OCT, WED
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Honduras(HolidayBase, ChristianHolidays, InternationalHolidays):
    # Artículo 339 del Código del Trabajo:
    # https://www.ilo.org/dyn/natlex/docs/WEBTEXT/29076/64849/S59HND01.htm

    country = "HN"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Maundy Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Holy Saturday.
        self._add_holy_saturday(tr("Sábado de Gloria"))

        # Panamerican Day.
        self._add_holiday(tr("Día de las Américas"), APR, 14)

        # Labor Day.
        self._add_labor_day(tr("Día del Trabajo"))

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), SEP, 15)

        # https://www.tsc.gob.hn/web/leyes/Decreto_78-2015_Traslado_de_Feriados_Octubre.pdf
        if year <= 2014:
            # Morazan's Day.
            self._add_holiday(tr("Día de Morazán"), OCT, 3)

            # Columbus Day.
            self._add_columbus_day(tr("Día de la Raza"))

            # Army Day.
            self._add_holiday(tr("Día de las Fuerzas Armadas"), OCT, 21)
        else:
            # Morazan Weekend.
            holiday_name = tr("Semana Morazánica")
            # First Wednesday of October from 12 noon to Saturday 12 noon.
            first_wednesday = self._get_nth_weekday_of_month(1, WED, OCT)
            self._add_holiday(holiday_name, first_wednesday)
            self._add_holiday(holiday_name, first_wednesday + td(days=+1))
            self._add_holiday(holiday_name, first_wednesday + td(days=+2))

        # Christmas.
        self._add_christmas_day(tr("Navidad"))


class HN(Honduras):
    pass


class HND(Honduras):
    pass
