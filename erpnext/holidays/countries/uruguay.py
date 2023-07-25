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

from holidays.calendars.gregorian import JAN, APR, MAY, JUN, JUL, AUG, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Uruguay(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Uruguay
    """

    country = "UY"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # Mandatory paid holidays:

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        # International Workers' Day.
        self._add_labor_day(tr("Día de los Trabajadores"))

        # Constitution Day.
        self._add_holiday(tr("Jura de la Constitución"), JUL, 18)

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), AUG, 25)

        # Day of the Family.
        self._add_christmas_day(tr("Día de la Familia"))

        # Partially paid holidays:

        # Children's Day.
        self._add_holiday(tr("Día de los Niños"), JAN, 6)

        # Birthday of José Gervasio Artigas.
        self._add_holiday(tr("Natalicio de José Gervasio Artigas"), JUN, 19)

        # All Souls' Day.
        self._add_all_souls_day(tr("Día de los Difuntos"))

        # Moveable holidays:

        # Carnival Day.
        name = tr("Día de Carnaval")
        self._add_carnival_monday(name)
        self._add_carnival_tuesday(name)

        # Maundy Thursday.
        self._add_holy_thursday(tr("Jueves Santo"))
        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))
        # Easter Day.
        self._add_easter_sunday(tr("Día de Pascuas"))

        holiday_pairs = (
            # Landing of the 33 Patriots.
            (date(year, APR, 19), tr("Desembarco de los 33 Orientales")),
            # Battle of Las Piedras.
            (date(year, MAY, 18), tr("Batalla de Las Piedras")),
            # Respect for Cultural Diversity Day.
            (date(year, OCT, 12), tr("Día del Respeto a la Diversidad Cultural")),
        )

        for dt, name in holiday_pairs:
            if self._is_tuesday(dt) or self._is_wednesday(dt):
                self._add_holiday(name, self._get_nth_weekday_from(-1, MON, dt))
            elif self._is_thursday(dt) or self._is_friday(dt):
                self._add_holiday(name, self._get_nth_weekday_from(1, MON, dt))
            else:
                self._add_holiday(name, dt)


class UY(Uruguay):
    pass


class URY(Uruguay):
    pass
