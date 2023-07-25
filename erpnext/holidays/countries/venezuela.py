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

from gettext import gettext as tr

from holidays.calendars.gregorian import APR, JUN, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Venezuela(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://dias-festivos.eu/dias-festivos/venezuela/#
    """

    country = "VE"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        """
        Overview: https://dias-festivos.eu/dias-festivos/venezuela/#
        Various decrees about holidays:
          1909 (AUG 5): https://bit.ly/3J0mWKQ
          1918 (MAY 19): https://bit.ly/3B8O1Jz
          1921 (JUN 11): https://bit.ly/3aUE2gz
          1971 (JUN 22): https://bit.ly/3yZaUN9
          2002 (OCT 10): https://bit.ly/3B7nRqC
          2012 (MAY 7): https://bit.ly/2MT5x97
        """

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Monday of Carnival.
        self._add_carnival_monday(tr("Lunes de Carnaval"))

        # Tuesday of Carnival.
        self._add_carnival_tuesday(tr("Martes de Carnaval"))

        # Maundy Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Note: not sure about the start year, but this event happened in 1811
        if year >= 1811:
            # Declaration of Independence.
            self._add_holiday(tr("Declaración de la Independencia"), APR, 19)

        # https://bit.ly/3B4Xd1L
        if year >= 1946:
            # International Worker's Day.
            self._add_labor_day(tr("Dia Mundial del Trabajador"))

        # Note: not sure about the start year, but this event happened in 1824
        if year >= 1971 or 1824 <= year <= 1917:
            # Battle of Carabobo.
            self._add_holiday(tr("Batalla de Carabobo"), JUN, 24)

        # Note: not sure about the start year, but this event happened in 1811
        if year >= 1811:
            # Independence Day.
            self._add_holiday(tr("Día de la Independencia"), JUL, 5)

        if year >= 1918:
            # Birthday of Simon Bolivar.
            self._add_holiday(tr("Natalicio de Simón Bolívar"), JUL, 24)

        if year >= 1921:
            self._add_columbus_day(
                # Day of Indigenous Resistance.
                tr("Día de la Resistencia Indígena")
                if year >= 2002
                # Columbus Day.
                else tr("Día de la Raza")
            )

        # Note: not sure about the start year nor the reason this was
        # Note: celebrated; the historical records are unclear
        if 1909 <= year <= 1917:
            # Unknown Holiday.
            self._add_holiday(tr("Día Festivo Desconocido"), OCT, 28)

        # Christmas Eve.
        self._add_christmas_eve(tr("Nochebuena"))

        # Christmas Day.
        self._add_christmas_day(tr("Día de Navidad"))

        # New Year's Eve.
        self._add_new_years_eve(tr("Fiesta de Fin de Año"))


class VE(Venezuela):
    pass


class VEN(Venezuela):
    pass
