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

from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class EuropeanCentralBank(HolidayBase, ChristianHolidays, InternationalHolidays):
    # https://en.wikipedia.org/wiki/TARGET2
    # http://www.ecb.europa.eu/press/pr/date/2000/html/pr001214_4.en.html

    market = "ECB"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        self._add_new_years_day("New Year's Day")

        self._add_good_friday("Good Friday")
        self._add_easter_monday("Easter Monday")

        self._add_labor_day("1 May (Labour Day)")

        self._add_christmas_day("Christmas Day")
        self._add_christmas_day_two("26 December")


class ECB(EuropeanCentralBank):
    pass


class TAR(EuropeanCentralBank):
    pass
