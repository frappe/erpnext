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

from holidays.calendars.gregorian import JAN, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Monaco(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Monaco
    https://en.service-public-entreprises.gouv.mc/Employment-and-social-affairs/Employment-regulations/Leave/Public-Holidays  # noqa: E501
    """

    country = "MC"
    default_language = "fr"
    special_holidays = {2015: (JAN, 7, tr("Jour férié"))}
    supported_languages = ("en_US", "fr", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_sunday(dt):
            self._add_holiday(self.tr("%s (Observé)") % self[dt], dt + td(days=days))

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_observed(self._add_new_years_day(tr("Le jour de l'An")))

        # Saint Devote's Day.
        self._add_holiday(tr("La Sainte Dévote"), JAN, 27)

        # Easter Monday.
        self._add_easter_monday(tr("Le lundi de Pâques"))

        # Labour Day.
        self._add_observed(self._add_labor_day(tr("Fête de la Travaille")))

        # Ascension's Day.
        self._add_ascension_thursday(tr("L'Ascension"))

        # Whit Monday.
        self._add_whit_monday(tr("Le lundi de Pentecôte"))

        # Corpus Christi.
        self._add_corpus_christi_day(tr("La Fête Dieu"))

        # Assumption's Day.
        self._add_observed(self._add_assumption_of_mary_day(tr("L'Assomption de Marie")))

        # All Saints' Day.
        self._add_observed(self._add_all_saints_day(tr("La Toussaint")))

        # Prince's Day.
        self._add_observed(self._add_holiday(tr("La Fête du Prince"), NOV, 19))

        dt = (DEC, 8)
        if year >= 2019 and self._is_sunday(*dt):
            dt = (DEC, 9)
        # Immaculate Conception's Day.
        self._add_holiday(tr("L'Immaculée Conception"), *dt)

        # Christmas Day.
        self._add_observed(self._add_christmas_day(tr("Noël")))


class MC(Monaco):
    pass


class MCO(Monaco):
    pass
