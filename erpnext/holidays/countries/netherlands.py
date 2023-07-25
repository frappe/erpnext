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

from holidays.calendars.gregorian import APR, MAY, AUG
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Netherlands(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_the_Netherlands
    http://www.iamsterdam.com/en/plan-your-trip/practical-info/public-holidays
    """

    country = "NL"
    default_language = "nl"
    supported_languages = ("en_US", "nl", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Nieuwjaarsdag"))

        # Good Friday.
        self._add_good_friday(tr("Goede Vrijdag"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Eerste paasdag"))

        # Easter Monday.
        self._add_easter_monday(tr("Tweede paasdag"))

        # King's / Queen's day
        if year >= 1891:
            name = (
                # King's Day.
                tr("Koningsdag")
                if year >= 2014
                # Queen's Day.
                else tr("Koninginnedag")
            )
            if year >= 2014:
                dt = date(year, APR, 27)
            elif year >= 1949:
                dt = date(year, APR, 30)
            else:
                dt = date(year, AUG, 31)
            if self._is_sunday(dt):
                dt += td(days=-1) if year >= 1980 else td(days=+1)
            self._add_holiday(name, dt)

        if year >= 1945 and year % 5 == 0:
            # Liberation Day.
            self._add_holiday(tr("Bevrijdingsdag"), MAY, 5)

        # Ascension Day.
        self._add_ascension_thursday(tr("Hemelvaartsdag"))

        # Whit Sunday.
        self._add_whit_sunday(tr("Eerste Pinksterdag"))

        # Whit Monday.
        self._add_whit_monday(tr("Tweede Pinksterdag"))

        # Christmas Day.
        self._add_christmas_day(tr("Eerste Kerstdag"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Tweede Kerstdag"))


class NL(Netherlands):
    pass


class NLD(Netherlands):
    pass
