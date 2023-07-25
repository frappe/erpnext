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
#  Copyright: Kateryna Golovanova <kate@kgthreads.com>, 2022

from gettext import gettext as tr

from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Liechtenstein(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Liechtenstein holidays.
    See https://en.wikipedia.org/wiki/Public_holidays_in_Liechtenstein
    for details.
    """

    country = "LI"
    default_language = "de"
    supported_languages = ("de", "en_US", "uk")

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Neujahr"))

        # Saint Berchtold's Day.
        self._add_new_years_day_two(tr("Berchtoldstag"))

        # Epiphany.
        self._add_epiphany_day(tr("Heilige Drei Könige"))

        # Candlemas.
        self._add_candlemas(tr("Mariä Lichtmess"))

        # Shrove Tuesday.
        self._add_carnival_tuesday(tr("Fasnachtsdienstag"))

        # Saint Joseph's Day.
        self._add_saint_josephs_day(tr("Josefstag"))

        # Good Friday.
        self._add_good_friday(tr("Karfreitag"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Ostersonntag"))

        # Easter Monday.
        self._add_easter_monday(tr("Ostermontag"))

        # Labor Day.
        self._add_labor_day(tr("Tag der Arbeit"))

        # Ascension Day.
        self._add_ascension_thursday(tr("Auffahrt"))

        # Whit Sunday.
        self._add_whit_sunday(tr("Pfingstsonntag"))

        # Whit Monday.
        self._add_whit_monday(tr("Pfingstmontag"))

        # Corpus Christi.
        self._add_corpus_christi_day(tr("Fronleichnam"))

        # National Day.
        self._add_assumption_of_mary_day(tr("Staatsfeiertag"))

        # Nativity of Mary.
        self._add_nativity_of_mary_day(tr("Mariä Geburt"))

        # All Saints Day.
        self._add_all_saints_day(tr("Allerheiligen"))

        # Immaculate Conception.
        self._add_immaculate_conception_day(tr("Mariä Empfängnis"))

        # Christmas Eve.
        self._add_christmas_eve(tr("Heiligabend"))

        # Christmas Day.
        self._add_christmas_day(tr("Weihnachten"))

        # St. Stephen's Day.
        self._add_christmas_day_two(tr("Stefanstag"))

        # New Year's Eve.
        self._add_new_years_eve(tr("Silvester"))


class LI(Liechtenstein):
    pass


class LIE(Liechtenstein):
    pass
