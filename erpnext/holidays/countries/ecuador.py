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

from holidays.calendars.gregorian import MAY, AUG, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Ecuador(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Ecuador
      - http://tiny.cc/ec_co_tr
    """

    country = "EC"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(
        self, dt: date, weekend_only: bool = False, before: bool = True, after: bool = True
    ) -> None:
        if self.observed and self._year >= 2017:
            obs_date = None
            # Art. 1 of Law #0 from 20.12.2016
            # When holidays falls on Tuesday, the rest shall be transferred to
            # preceding Monday, and if they falls on Wednesday or Thursday,
            # the rest shall be transferred to Friday of the same week.
            # Exceptions to this provision are January 1, December 25 and
            # Shrove Tuesday.
            if not weekend_only:
                if self._is_tuesday(dt) and before:
                    obs_date = dt + td(days=-1)
                elif self._is_wednesday(dt):
                    obs_date = dt + td(days=+2)
                elif self._is_thursday(dt) and after:
                    obs_date = dt + td(days=+1)
            # When holidays falls on Saturday or Sunday, the rest shall be
            # transferred, respectively, to the preceding Friday or the
            # following Monday.
            if self._is_saturday(dt) and before:
                obs_date = dt + td(days=-1)
            elif self._is_sunday(dt) and after:
                obs_date = dt + td(days=+1)
            if obs_date:
                self._add_holiday(self.tr("%s (Observado)") % self[dt], obs_date)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        name = self.tr("Año Nuevo")
        self._add_observed(self._add_new_years_day(name), weekend_only=True)

        if self.observed and year >= 2017:
            if self._is_friday(DEC, 31):
                self._add_holiday(self.tr("%s (Observado)") % name, DEC, 31)

        # Carnival.
        name = tr("Carnaval")
        self._add_carnival_monday(name)
        self._add_carnival_tuesday(name)

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Labour Day.
        self._add_observed(self._add_labor_day(tr("Día del Trabajo")))

        # The Battle of Pichincha.
        self._add_observed(self._add_holiday(tr("Batalla de Pichincha"), MAY, 24))

        # Declaration of Independence of Quito.
        self._add_observed(self._add_holiday(tr("Primer Grito de Independencia"), AUG, 10))

        # Independence of Guayaquil.
        self._add_observed(self._add_holiday(tr("Independencia de Guayaquil"), OCT, 9))

        # All Souls' Day.
        self._add_observed(self._add_all_souls_day(tr("Día de los Difuntos")), after=False)

        # Independence of Cuenca.
        self._add_observed(self._add_holiday(tr("Independencia de Cuenca"), NOV, 3), before=False)

        # Christmas Day.
        self._add_observed(self._add_christmas_day(tr("Día de Navidad")), weekend_only=True)


class EC(Ecuador):
    pass


class ECU(Ecuador):
    pass
