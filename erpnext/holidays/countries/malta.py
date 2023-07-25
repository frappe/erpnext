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

from holidays.calendars.gregorian import FEB, MAR, JUN, SEP, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Malta(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.gov.mt/en/About%20Malta/Pages/Public%20Holidays.aspx

    [Att 10 tal-1980]
        Oldest Maltese Holidays Law available online in full.
        https://legislation.mt/eli/act/1980/10/mlt
    [A.L. 40 tal-1987]
        Additional Holidays added.
        https://legislation.mt/eli/ln/1987/8/mlt
    [Att 8 tal-1989]
        Additional Holidays added.
        https://legislation.mt/eli/act/1989/8
    [Att 2 tal-2005]
        If fall on weekends then not observed in terms of vacation leave.
        https://legislation.mt/eli/act/2005/2/eng
    [Att 4 tal-2021]
        Revert Act II of 2005 changes for vacation leave.
        https://legislation.mt/eli/cap/252/20210212/mlt
    """

    country = "MT"
    default_language = "mt"
    supported_languages = ("en_MT", "mt")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # Earliest available source is 1980
        if year <= 1979:
            return None
        super()._populate(year)

        # L-Ewwel tas-Sena
        # Status: In-Use.

        # New Year's Day
        self._add_new_years_day(tr("L-Ewwel tas-Sena"))

        # Il-Festa tan-Nawfraġju ta' San Pawl
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.

        if year >= 1987:
            # Feast of St. Paul's Shipwreck
            self._add_holiday(tr("Il-Festa tan-Nawfraġju ta' San Pawl"), FEB, 10)

        # Il-Festa ta' San Ġużepp
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.

        if year >= 1987:
            # Feast of St. Joseph
            self._add_saint_josephs_day(tr("Il-Festa ta' San Ġużepp"))

        # Jum il-Ħelsien
        # Status: In-Use.
        # Started in 1980 Act X of 1980.
        # Not presented in 1987-1988

        if year <= 1986 or year >= 1989:
            # Freedom Day
            self._add_holiday(tr("Jum il-Ħelsien"), MAR, 31)

        # Il-Ġimgħa l-Kbira
        # Status: In-Use.

        # Good Friday
        self._add_good_friday(tr("Il-Ġimgħa l-Kbira"))

        # Jum il-Ħaddiem
        # Status: In-Use.

        # Worker's Day
        self._add_labor_day(tr("Jum il-Ħaddiem"))

        # Sette Giugno
        # Status: In-Use.
        # Start in 1989 via Act VIII of 1989.

        if year >= 1989:
            # Sette Giugno
            self._add_holiday(tr("Sette Giugno"), JUN, 7)

        # Il-Festa ta' San Pietru u San Pawl
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.

        if year >= 1987:
            # Feast of St. Peter and St. Paul
            self._add_saints_peter_and_paul_day(tr("Il-Festa ta' San Pietru u San Pawl"))

        # Il-Festa ta' Santa Marija
        # Status: In-Use.

        # Feast of the Assumption
        self._add_assumption_of_mary_day(tr("Il-Festa ta' Santa Marija"))

        # Jum il-Vitorja
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.
        # While this concides with Nativity Of Mary Day, the two are considered separate.

        if year >= 1987:
            # Feast of Our Lady of Victories
            self._add_holiday(tr("Jum il-Vitorja"), SEP, 8)

        # Jum l-Indipendenza
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.

        if year >= 1987:
            # Independence Day
            self._add_holiday(tr("Jum l-Indipendenza"), SEP, 21)

        # Il-Festa tal-Immakulata Kunċizzjoni
        # Status: In-Use.
        # Started in 1987 via Act LX of 1987.

        if year >= 1987:
            # Feast of the Immaculate Conception
            self._add_immaculate_conception_day(tr("Il-Festa tal-Immakulata Kunċizzjoni"))

        # Jum ir-Repubblika
        # Status: In-Use.

        # Republic Day
        self._add_holiday(tr("Jum ir-Repubblika"), DEC, 13)

        # Il-Milied
        # Status: In-Use.

        # Christmas Day
        self._add_christmas_day(tr("Il-Milied"))


class MT(Malta):
    pass


class MLT(Malta):
    pass
