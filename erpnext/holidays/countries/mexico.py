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

from holidays.calendars.gregorian import FEB, MAR, SEP, NOV, DEC, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Mexico(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Mexico
    - https://es.wikipedia.org/wiki/Anexo:D%C3%ADas_festivos_en_M%C3%A9xico
    - https://www.gob.mx/cms/uploads/attachment/file/156203/1044_Ley_Federal_del_Trabajo.pdf
    - http://www.diputados.gob.mx/LeyesBiblio/ref/lft/LFT_orig_01abr70_ima.pdf
    """

    country = "MX"
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

        if year >= 1917:
            self._add_holiday(
                # Constitution Day.
                tr("Día de la Constitución"),
                self._get_nth_weekday_of_month(1, MON, FEB)
                if year >= 2006
                else date(year, FEB, 5),
            )

        if year >= 1917:
            self._add_holiday(
                # Benito Juárez's birthday.
                tr("Natalicio de Benito Juárez"),
                self._get_nth_weekday_of_month(3, MON, MAR)
                # no 2006 due to celebration of the 200th anniversary
                # of Benito Juárez in 2006
                if year >= 2007 else date(year, MAR, 21),
            )

        if year >= 1923:
            # Labor Day.
            self._add_labor_day(tr("Día del Trabajo"))

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), SEP, 16)

        if year >= 1917:
            self._add_holiday(
                # Revolution Day.
                tr("Día de la Revolución"),
                self._get_nth_weekday_of_month(3, MON, NOV)
                if year >= 2006
                else date(year, NOV, 20),
            )

        if year >= 1970 and (year - 1970) % 6 == 0:
            # Change of Federal Government.
            self._add_holiday(tr("Transmisión del Poder Ejecutivo Federal"), DEC, 1)

        # Christmas Day.
        self._add_christmas_day(tr("Navidad"))


class MX(Mexico):
    pass


class MEX(Mexico):
    pass
