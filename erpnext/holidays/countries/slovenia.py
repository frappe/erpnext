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

from holidays.calendars.gregorian import FEB, APR, JUN, OCT, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Slovenia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Contains all work-free public holidays in Slovenia.
    No holidays are returned before year 1991 when Slovenia became independent
    country. Before that Slovenia was part of Socialist federal republic of
    Yugoslavia.

    List of holidays (including those that are not work-free:
    https://en.wikipedia.org/wiki/Public_holidays_in_Slovenia
    """

    country = "SI"
    default_language = "sl"
    supported_languages = ("en_US", "sl", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1990:
            return None

        super()._populate(year)

        # New Year's Day.
        name = tr("novo leto")
        self._add_new_years_day(name)
        if year <= 2012 or year >= 2017:
            self._add_new_years_day_two(name)

        # Preseren's Day.
        self._add_holiday(tr("Prešernov dan"), FEB, 8)

        # Easter Monday.
        self._add_easter_monday(tr("Velikonočni ponedeljek"))

        # Day of Uprising Against Occupation.
        self._add_holiday(tr("dan upora proti okupatorju"), APR, 27)

        # Labor Day.
        name = tr("praznik dela")
        self._add_labor_day(name)
        self._add_labor_day_two(name)

        # Statehood Day.
        self._add_holiday(tr("dan državnosti"), JUN, 25)

        # Assumption Day.
        self._add_assumption_of_mary_day(tr("Marijino vnebovzetje"))

        if year >= 1992:
            # Reformation Day.
            self._add_holiday(tr("dan reformacije"), OCT, 31)

        # Remembrance Day.
        self._add_all_saints_day(tr("dan spomina na mrtve"))

        # Christmas Day.
        self._add_christmas_day(tr("Božič"))

        # Independence and Unity Day.
        self._add_holiday(tr("dan samostojnosti in enotnosti"), DEC, 26)


class SI(Slovenia):
    pass


class SVN(Slovenia):
    pass
