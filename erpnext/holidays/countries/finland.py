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

from holidays.calendars.gregorian import JAN, MAY, JUN, OCT, NOV, DEC, FRI, SAT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Finland(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Finland
    """

    country = "FI"
    default_language = "fi"
    supported_languages = ("en_US", "fi", "sv", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Uudenvuodenpäivä"))

        # Epiphany.
        name = tr("Loppiainen")
        if 1973 <= year <= 1990:
            self._add_holiday(name, self._get_nth_weekday_from(1, SAT, JAN, 6))
        else:
            self._add_epiphany_day(name)

        # Good Friday.
        self._add_good_friday(tr("Pitkäperjantai"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Pääsiäispäivä"))

        # Easter Monday.
        self._add_easter_monday(tr("2. pääsiäispäivä"))

        # May Day.
        self._add_holiday(tr("Vappu"), MAY, 1)

        # Ascension Day.
        name = tr("Helatorstai")
        if 1973 <= year <= 1990:
            self._add_holiday(name, self._easter_sunday + td(days=+34))
        else:
            self._add_ascension_thursday(name)

        # Whit Sunday.
        self._add_whit_sunday(tr("Helluntaipäivä"))

        dt = self._get_nth_weekday_from(1, FRI, JUN, 19) if year >= 1955 else date(year, JUN, 23)
        # Midsummer Eve.
        self._add_holiday(tr("Juhannusaatto"), dt)
        # Midsummer Day.
        self._add_holiday(tr("Juhannuspäivä"), dt + td(days=+1))

        dt = self._get_nth_weekday_from(1, SAT, OCT, 31) if year >= 1955 else date(year, NOV, 1)
        # All Saints' Day.
        self._add_holiday(tr("Pyhäinpäivä"), dt)

        # Independence Day.
        self._add_holiday(tr("Itsenäisyyspäivä"), DEC, 6)

        # Christmas Eve.
        self._add_christmas_eve(tr("Jouluaatto"))

        # Christmas Day.
        self._add_christmas_day(tr("Joulupäivä"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Tapaninpäivä"))


class FI(Finland):
    pass


class FIN(Finland):
    pass
