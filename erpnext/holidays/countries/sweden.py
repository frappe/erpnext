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

from holidays.calendars.gregorian import JAN, MAR, JUN, OCT, DEC, FRI, SAT, SUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Sweden(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Swedish holidays.
    Note that holidays falling on a sunday are "lost",
    it will not be moved to another day to make up for the collision.
    In Sweden, ALL sundays are considered a holiday
    (https://sv.wikipedia.org/wiki/Helgdagar_i_Sverige).
    Initialize this class with include_sundays=False
    to not include sundays as a holiday.
    Primary sources:
    https://sv.wikipedia.org/wiki/Helgdagar_i_Sverige and
    http://www.riksdagen.se/sv/dokument-lagar/dokument/svensk-forfattningssamling/lag-1989253-om-allmanna-helgdagar_sfs-1989-253
    """

    country = "SE"
    default_language = "sv"
    supported_languages = ("en_US", "sv", "uk")

    def __init__(self, include_sundays=True, **kwargs):
        """
        :param include_sundays: Whether to consider sundays as a holiday
        (which they are in Sweden)
        :param kwargs:
        """
        self.include_sundays = include_sundays
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        HolidayBase.__init__(self, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Nyårsdagen"))

        # Epiphany.
        self._add_epiphany_day(tr("Trettondedag jul"))

        if year <= 1953:
            # Feast of the Annunciation.
            self._add_holiday(tr("Jungfru Marie bebådelsedag"), MAR, 25)

        # Good Friday.
        self._add_good_friday(tr("Långfredagen"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Påskdagen"))

        # Easter Monday.
        self._add_easter_monday(tr("Annandag påsk"))

        # Source: https://sv.wikipedia.org/wiki/F%C3%B6rsta_maj
        if year >= 1939:
            # May Day.
            self._add_labor_day(tr("Första maj"))

        # Ascension Day.
        self._add_ascension_thursday(tr("Kristi himmelsfärdsdag"))

        # Source: https://sv.wikipedia.org/wiki/Sveriges_nationaldag
        if year >= 2005:
            # National Day of Sweden.
            self._add_holiday(tr("Sveriges nationaldag"), JUN, 6)

        # Whit Sunday.
        self._add_whit_sunday(tr("Pingstdagen"))

        if year <= 2004:
            # Whit Monday.
            self._add_whit_monday(tr("Annandag pingst"))

        # Source:
        # https://sv.wikipedia.org/wiki/Midsommarafton
        # https://www.nordiskamuseet.se/aretsdagar/midsommarafton
        # Midsummer evening. Friday between June 19th and June 25th
        dt = self._get_nth_weekday_from(1, FRI, JUN, 19) if year >= 1953 else date(year, JUN, 23)
        # Midsummer Eve.
        self._add_holiday(tr("Midsommarafton"), dt)

        # Midsummer Day.
        self._add_holiday(tr("Midsommardagen"), dt + td(days=+1))

        # All Saints' Day.
        self._add_holiday(tr("Alla helgons dag"), self._get_nth_weekday_from(1, SAT, OCT, 31))

        # Christmas Eve.
        self._add_christmas_eve(tr("Julafton"))

        # Christmas Day.
        self._add_christmas_day(tr("Juldagen"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Annandag jul"))

        # New Year's Eve.
        self._add_new_years_eve(tr("Nyårsafton"))

        if self.include_sundays:
            # Optionally add all Sundays of the year.
            begin = self._get_nth_weekday_of_month(1, SUN, JAN)
            end = date(year, DEC, 31)
            for dt in (begin + td(days=n) for n in range(0, (end - begin).days + 1, 7)):
                # Sunday.
                self._add_holiday(tr("Söndag"), dt)


class SE(Sweden):
    pass


class SWE(Sweden):
    pass
