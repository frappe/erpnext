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

from datetime import timedelta as td
from gettext import gettext as tr

from holidays.calendars.gregorian import MAY, JUL, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Poland(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://pl.wikipedia.org/wiki/Dni_wolne_od_pracy_w_Polsce
    """

    country = "PL"
    default_language = "pl"
    special_holidays = {2018: (NOV, 12, tr("Narodowe Święto Niepodległości - 100-lecie"))}
    supported_languages = ("en_US", "pl", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1924:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Nowy Rok"))

        if year <= 1960 or year >= 2011:
            # Epiphany.
            self._add_epiphany_day(tr("Święto Trzech Króli"))

        if year <= 1950:
            # Candlemas.
            self._add_candlemas(tr("Oczyszczenie Najświętszej Marii Panny"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Niedziela Wielkanocna"))

        # Easter Monday.
        self._add_easter_monday(tr("Poniedziałek Wielkanocny"))

        if year >= 1950:
            # National Day.
            self._add_holiday(tr("Święto Państwowe"), MAY, 1)

        if year <= 1950 or year >= 1990:
            # National Day of the Third of May.
            self._add_holiday(tr("Święto Narodowe Trzeciego Maja"), MAY, 3)

        if 1946 <= year <= 1950:
            # National Victory and Freedom Day.
            self._add_holiday(tr("Narodowe Święto Zwycięstwa i Wolności"), MAY, 9)

        if year <= 1950:
            # Ascension Day.
            self._add_holiday(tr("Wniebowstąpienie Pańskie"), self._easter_sunday + td(days=+40))

        # Pentecost.
        self._add_whit_sunday(tr("Zielone Świątki"))

        if year <= 1950:
            # Pentecost (Day 2).
            self._add_whit_monday(tr("Drugi dzień Zielonych Świątek"))

        # Corpus Christi.
        self._add_corpus_christi_day(tr("Dzień Bożego Ciała"))

        if year <= 1950:
            self._add_saints_peter_and_paul_day(
                # Saints Peter and Paul Day.
                tr("Uroczystość Świętych Apostołów Piotra i Pawła")
            )

        if 1945 <= year <= 1989:
            # National Day of Rebirth of Poland.
            self._add_holiday(tr("Narodowe Święto Odrodzenia Polski"), JUL, 22)

        if year <= 1960 or year >= 1989:
            # Assumption of the Virgin Mary.
            self._add_assumption_of_mary_day(tr("Wniebowzięcie Najświętszej Marii Panny"))

        # All Saints' Day.
        self._add_all_saints_day(tr("Uroczystość Wszystkich Świętych"))

        if 1937 <= year <= 1944 or year >= 1989:
            # National Independence Day.
            self._add_holiday(tr("Narodowe Święto Niepodległości"), NOV, 11)

        if year <= 1950:
            self._add_immaculate_conception_day(
                # Immaculate Conception of the Blessed Virgin Mary.
                tr("Niepokalane Poczęcie Najświętszej Marii Panny")
            )

        # Christmas Day 1.
        self._add_christmas_day(tr("Boże Narodzenie (pierwszy dzień)"))
        # Christmas Day 2.
        self._add_christmas_day_two(tr("Boże Narodzenie (drugi dzień)"))


class PL(Poland):
    pass


class POL(Poland):
    pass
