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

from holidays.calendars.gregorian import JAN, MAY, JUL, SEP, OCT, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Czechia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_the_Czech_Republic
    """

    country = "CZ"
    default_language = "cs"
    supported_languages = ("cs", "en_US", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        self._add_holiday(
            # Independent Czech State Restoration Day.
            tr("Den obnovy samostatného českého státu") if year >= 2000
            # New Year's Day.
            else tr("Nový rok"),
            JAN,
            1,
        )

        if year <= 1951 or year >= 2016:
            # Good Friday.
            self._add_good_friday(tr("Velký pátek"))

        # Easter Monday.
        self._add_easter_monday(tr("Velikonoční pondělí"))

        if year >= 1951:
            # Labor Day.
            self._add_labor_day(tr("Svátek práce"))

        if year >= 1992:
            # Victory Day.
            self._add_holiday(tr("Den vítězství"), MAY, 8)
        elif year >= 1947:
            # Day of Victory over Fascism.
            self._add_world_war_two_victory_day(tr("Den vítězství nad hitlerovským fašismem"))

        if year >= 1951:
            # Saints Cyril and Methodius Day.
            self._add_holiday(tr("Den slovanských věrozvěstů Cyrila a Metoděje"), JUL, 5)

            # Jan Hus Day.
            self._add_holiday(tr("Den upálení mistra Jana Husa"), JUL, 6)

        if year >= 2000:
            # Statehood Day.
            self._add_holiday(tr("Den české státnosti"), SEP, 28)

        if year >= 1951:
            # Independent Czechoslovak State Day.
            self._add_holiday(tr("Den vzniku samostatného československého státu"), OCT, 28)

        if year >= 1990:
            # Struggle for Freedom and Democracy Day.
            self._add_holiday(tr("Den boje za svobodu a demokracii"), NOV, 17)

            # Christmas Eve.
            self._add_christmas_eve(tr("Štědrý den"))

        if year >= 1951:
            # Christmas Day.
            self._add_christmas_day(tr("1. svátek vánoční"))

            # Second Day of Christmas.
            self._add_christmas_day_two(tr("2. svátek vánoční"))


class CZ(Czechia):
    pass


class CZE(Czechia):
    pass
