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
from gettext import gettext as tr

from holidays.calendars.gregorian import JAN, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Cuba(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Overview: https://en.wikipedia.org/wiki/Public_holidays_in_Cuba
    1984 (DEC 28): https://bit.ly/3okNBbt
    2007 (NOV 19): https://bit.ly/3oFbhaZ
    2013 (DEC 20): https://bit.ly/3zoO3vC
    Note: for holidays that can be moved to a Monday if they fall on a
            Sunday, between 1984 and 2013, the State Committee of Work and
            Social Security would determine if they would be moved to the
            Monday, or if they would stay on the Sunday, presumably depending
            on quotas. After 2013, they always move to Monday. I could not
            find any records of this, so I implemented this making it always
            go to the next Monday.
    """

    country = "CU"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # This calendar only works from 1959 onwards.
        if year <= 1958:
            return None

        def _add_observed(hol_date: date) -> None:
            if self.observed and self._is_sunday(hol_date):
                self._add_holiday(
                    self.tr("%s (Observado)") % self[hol_date], hol_date + td(days=+1)
                )

        super()._populate(year)

        # Liberation Day.
        jan_1 = self._add_holiday(tr("Triunfo de la Revolución"), JAN, 1)
        if year <= 2013:
            _add_observed(jan_1)

        # Granted in 2007 decree.
        if year >= 2008:
            #  Victory Day.
            self._add_holiday(tr("Día de la Victoria"), JAN, 2)

        # Granted temporarily in 2012 and 2013:
        #   https://cnn.it/3v5V6GY
        #   https://bit.ly/3v6bM18
        # Permanently granted in 2013 decree for 2014 and onwards.
        if year >= 2012:
            # Good Friday.
            self._add_good_friday(tr("Viernes Santo"))

        # Labour Day.
        _add_observed(self._add_labor_day(tr("Día Internacional de los Trabajadores")))

        # Commemoration of the Assault of the Moncada garrison.
        self._add_holiday(tr("Conmemoración del asalto a Moncada"), JUL, 25)

        # Day of the National Rebellion.
        self._add_holiday(tr("Día de la Rebeldía Nacional"), JUL, 26)

        # Commemoration of the Assault of the Moncada garrison.
        self._add_holiday(tr("Conmemoración del asalto a Moncada"), JUL, 27)

        # Independence Day.
        _add_observed(self._add_holiday(tr("Inicio de las Guerras de Independencia"), OCT, 10))

        # In 1969, Christmas was cancelled for the sugar harvest but then was
        # cancelled for good:
        #   https://bit.ly/3OpwX5i
        # In 1997, Christmas was temporarily back for the pope's visit:
        #   https://cnn.it/3Omn349
        # In 1998, Christmas returns for good:
        #   https://bit.ly/3cyXhwz
        #   https://bit.ly/3cyXj7F
        if year <= 1968 or year >= 1997:
            # Christmas Day.
            self._add_christmas_day(tr("Día de Navidad"))

        # Granted in 2007 decree.
        if year >= 2007:
            # New Year's Eve.
            self._add_new_years_eve(tr("Fiesta de Fin de Año"))


class CU(Cuba):
    pass


class CUB(Cuba):
    pass
