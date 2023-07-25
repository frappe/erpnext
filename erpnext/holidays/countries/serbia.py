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

from holidays.calendars.gregorian import FEB
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Serbia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Serbia holidays.

    References:
     - https://en.wikipedia.org/wiki/Public_holidays_in_Serbia
    """

    country = "RS"
    default_language = "sr"
    supported_languages = ("en_US", "sr")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_sunday(dt):
            self._add_holiday(self.tr("%s (слободан дан)") % self[dt], dt + td(days))

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        name = tr("Нова година")
        self._add_observed(self._add_new_years_day(name), days=+2)
        self._add_observed(self._add_new_years_day_two(name))

        # Orthodox Christmas.
        self._add_christmas_day(tr("Божић"))

        # Statehood Day.
        name = tr("Дан државности Србије")
        self._add_observed(self._add_holiday(name, FEB, 15), days=+2)
        self._add_observed(self._add_holiday(name, FEB, 16))

        # International Workers' Day.
        name = tr("Празник рада")
        self._add_observed(self._add_labor_day(name), days=+2)
        may_2 = self._add_labor_day_two(name)
        self._add_observed(may_2, days=+2 if may_2 == self._easter_sunday else +1)

        # Armistice Day.
        self._add_observed(self._add_remembrance_day(tr("Дан примирја у Првом светском рату")))

        # Good Friday.
        self._add_good_friday(tr("Велики петак"))
        # Easter Saturday.
        self._add_holy_saturday(tr("Велика субота"))
        # Easter Sunday.
        self._add_easter_sunday(tr("Васкрс"))
        # Easter Monday.
        self._add_easter_monday(tr("Други дан Васкрса"))


class RS(Serbia):
    pass


class SRB(Serbia):
    pass
