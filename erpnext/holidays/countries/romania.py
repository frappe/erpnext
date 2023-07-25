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

from holidays.calendars.gregorian import GREGORIAN_CALENDAR, JAN, NOV, DEC
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Romania(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Romania
    http://www.dreptonline.ro/legislatie/codul_muncii.php
    """

    country = "RO"
    default_language = "ro"
    supported_languages = ("en_US", "ro", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        name = tr("Anul Nou")
        self._add_new_years_day(name)
        self._add_new_years_day_two(name)

        if year >= 2024:
            # Epiphany.
            self._add_epiphany_day(tr("Bobotează"), GREGORIAN_CALENDAR)

            # Saint John the Baptist.
            self._add_holiday(tr("Sfântul Ion"), JAN, 7)

        if year >= 2016:
            # Unification of the Romanian Principalities Day.
            self._add_holiday(tr("Ziua Unirii Principatelor Române"), JAN, 24)

        # Easter.
        name = tr("Paștele")
        if year >= 2018:
            self._add_good_friday(name)

        self._add_easter_sunday(name)
        self._add_easter_monday(name)

        # Labour Day.
        self._add_labor_day(tr("Ziua Muncii"))

        if year >= 2017:
            # Children's Day.
            self._add_childrens_day(tr("Ziua Copilului"))

        # Pentecost.
        name = tr("Rusaliile")
        self._add_whit_sunday(name)
        self._add_whit_monday(name)

        # Law #202/2008
        if year >= 2009:
            # Dormition of the Mother of God.
            self._add_assumption_of_mary_day(tr("Adormirea Maicii Domnului"))

        # Law #147/2012
        if year >= 2012:
            # Saint Andrew's Day.
            self._add_holiday(tr("Sfantul Apostol Andrei cel Intai chemat"), NOV, 30)

        # National Day.
        self._add_holiday(tr("Ziua Națională a României"), DEC, 1)

        # Christmas Day.
        name = tr("Crăciunul")
        self._add_christmas_day(name, GREGORIAN_CALENDAR)
        self._add_christmas_day_two(name, GREGORIAN_CALENDAR)


class RO(Romania):
    pass


class ROU(Romania):
    pass
