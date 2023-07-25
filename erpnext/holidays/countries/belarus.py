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

from holidays.calendars.gregorian import GREGORIAN_CALENDAR, JUL, NOV
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Belarus(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Belarus holidays.

    References:
     - http://president.gov.by/en/holidays_en/
     - http://www.belarus.by/en/about-belarus/national-holidays
    """

    country = "BY"
    default_language = "be"
    supported_languages = ("be", "en_US")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # The current set of holidays came into force in 1998.
        # http://laws.newsby.org/documents/ukazp/pos05/ukaz05806.htm
        if year <= 1998:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Новы год"))

        # Jan 2nd is the national holiday (New Year) from 2020.
        # http://president.gov.by/uploads/documents/2019/464uk.pdf
        if year >= 2020:
            self._add_new_years_day_two(tr("Новы год"))

        # Orthodox Christmas Day.
        self._add_christmas_day(tr("Нараджэнне Хрыстова (праваслаўнае Раство)"))

        # Women's Day.
        self._add_womens_day(tr("Дзень жанчын"))

        # Radunitsa (Day of Rejoicing).
        self._add_rejoicing_day(tr("Радаўніца"))

        # Labour Day.
        self._add_labor_day(tr("Свята працы"))

        # Victory Day.
        self._add_world_war_two_victory_day(tr("Дзень Перамогі"))

        # Independence Day.
        self._add_holiday(tr("Дзень Незалежнасці Рэспублікі Беларусь (Дзень Рэспублікі)"), JUL, 3)

        # October Revolution Day.
        self._add_holiday(tr("Дзень Кастрычніцкай рэвалюцыі"), NOV, 7)

        # Catholic Christmas Day.
        self._add_christmas_day(tr("Нараджэнне Хрыстова (каталіцкае Раство)"), GREGORIAN_CALENDAR)


class BY(Belarus):
    pass


class BLR(Belarus):
    pass
