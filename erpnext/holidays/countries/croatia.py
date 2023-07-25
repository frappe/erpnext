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

from holidays.calendars.gregorian import MAY, JUN, AUG, OCT, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Croatia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Updated with act 022-03 / 19-01 / 219 of 14 November 2019
    https://narodne-novine.nn.hr/clanci/sluzbeni/2019_11_110_2212.html
    https://en.wikipedia.org/wiki/Public_holidays_in_Croatia
    https://hr.wikipedia.org/wiki/Blagdani_i_spomendani_u_Hrvatskoj
    """

    country = "HR"
    default_language = "hr"
    supported_languages = ("en_US", "hr", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Nova Godina"))

        if year != 2002:
            # Epiphany.
            self._add_epiphany_day(tr("Bogojavljenje ili Sveta tri kralja"))

        if year >= 2009:
            # Easter.
            self._add_easter_sunday(tr("Uskrs"))

        # Easter Monday.
        self._add_easter_monday(tr("Uskrsni ponedjeljak"))

        if year >= 2002:
            # Corpus Christi.
            self._add_corpus_christi_day(tr("Tijelovo"))

        # International Workers' Day.
        self._add_labor_day(tr("Međunarodni praznik rada"))

        if year >= 1996:
            self._add_holiday(
                # Statehood Day.
                tr("Dan državnosti"),
                *((JUN, 25) if 2002 <= year <= 2019 else (MAY, 30)),
            )

        # Anti-Fascist Struggle Day.
        self._add_holiday(tr("Dan antifašističke borbe"), JUN, 22)

        name = (
            # Victory and Homeland Thanksgiving Day and Croatian Veterans Day.
            tr("Dan pobjede i domovinske zahvalnosti i Dan hrvatskih branitelja")
            if year >= 2008
            # Victory and Homeland Thanksgiving Day.
            else tr("Dan pobjede i domovinske zahvalnosti")
        )
        self._add_holiday(name, AUG, 5)

        # Assumption of Mary.
        self._add_assumption_of_mary_day(tr("Velika Gospa"))

        if 2002 <= year <= 2019:
            # Independence Day.
            self._add_holiday(tr("Dan neovisnosti"), OCT, 8)

        # All Saints' Day.
        self._add_all_saints_day(tr("Svi sveti"))

        if year >= 2020:
            # Memorial Day.
            self._add_holiday(tr("Dan sjećanja"), NOV, 18)

        # Christmas Day.
        self._add_christmas_day(tr("Božić"))

        # St. Stephen's Day.
        self._add_christmas_day_two(tr("Sveti Stjepan"))


class HR(Croatia):
    pass


class HRV(Croatia):
    pass
