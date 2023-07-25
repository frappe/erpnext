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

from holidays.calendars.gregorian import JUL, AUG, SEP
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Nicaragua(HolidayBase, ChristianHolidays, InternationalHolidays):
    country = "NI"
    default_language = "es"
    subdivisions = (
        "AN",
        "AS",
        "BO",
        "CA",
        "CI",
        "CO",
        "ES",
        "GR",
        "JI",
        "LE",
        "MD",
        "MN",
        "MS",
        "MT",
        "NS",
        "RI",
        "SJ",
    )
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        # Default subdivision to MN; prov for backwards compatibility
        if not kwargs.get("subdiv", kwargs.get("prov")):
            kwargs["subdiv"] = "MN"
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # Maundy Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Labor Day.
        self._add_labor_day(tr("Día del Trabajo"))

        if year >= 1979:
            # Revolution Day.
            self._add_holiday(tr("Día de la Revolución"), JUL, 19)

        # Battle of San Jacinto Day.
        self._add_holiday(tr("Batalla de San Jacinto"), SEP, 14)

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), SEP, 15)

        # Virgin's Day.
        self._add_immaculate_conception_day(tr("Concepción de María"))

        # Christmas.
        self._add_christmas_day(tr("Navidad"))

    def _add_subdiv_mn_holidays(self):
        # Descent of Saint Dominic.
        self._add_holiday(tr("Bajada de Santo Domingo"), AUG, 1)

        # Ascent of Saint Dominic.
        self._add_holiday(tr("Subida de Santo Domingo"), AUG, 10)


class NI(Nicaragua):
    pass


class NIC(Nicaragua):
    pass
