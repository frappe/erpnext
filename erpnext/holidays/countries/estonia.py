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

from holidays.calendars.gregorian import FEB, MAY, JUN, AUG
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Estonia(HolidayBase, ChristianHolidays, InternationalHolidays):
    country = "EE"
    default_language = "et"
    supported_languages = ("en_US", "et", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("uusaasta"))

        # Independence Day.
        self._add_holiday(tr("iseseisvuspäev"), FEB, 24)

        # Good Friday.
        self._add_good_friday(tr("suur reede"))

        # Easter Sunday.
        self._add_easter_sunday(tr("ülestõusmispühade 1. püha"))

        # Spring Day.
        self._add_holiday(tr("kevadpüha"), MAY, 1)

        # Whit Sunday.
        self._add_whit_sunday(tr("nelipühade 1. püha"))

        # Victory Day.
        self._add_holiday(tr("võidupüha"), JUN, 23)

        # Midsummer Day.
        self._add_saint_johns_day(tr("jaanipäev"))

        if year >= 1998:
            # Independence Restoration Day.
            self._add_holiday(tr("taasiseseisvumispäev"), AUG, 20)

        if year >= 2005:
            # Christmas Eve.
            self._add_christmas_eve(tr("jõululaupäev"))

        # Christmas Day.
        self._add_christmas_day(tr("esimene jõulupüha"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("teine jõulupüha"))


class EE(Estonia):
    pass


class EST(Estonia):
    pass
