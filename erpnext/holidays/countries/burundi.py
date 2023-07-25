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
from typing import Optional

from holidays.calendars.gregorian import FEB, APR, JUN, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Burundi(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    Burundian holidays
    Note that holidays falling on a sunday maybe observed
    on the following Monday.
    This depends on formal annoucemnts by the government,
    which only happens close to the date of the holiday.

    Primary sources:
    https://www.officeholidays.com/countries/burundi
    """

    country = "BI"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_holiday(self, *args) -> Optional[date]:
        dt = super()._add_holiday(*args)
        if self.observed and dt and self._is_sunday(dt):
            super()._add_holiday(
                "%s (Observed)" % self[dt], dt + td(days=+1)  # type: ignore[index, operator]
            )
        return dt

    def _populate(self, year):
        if year <= 1961:
            return None

        super()._populate(year)

        # New Year's Day
        self._add_new_years_day("New Year's Day")

        # Unity Day
        if year >= 1992:
            self._add_holiday("Unity Day", FEB, 5)

        # President Ntaryamira Day
        if year >= 1995:
            self._add_holiday("President Ntaryamira Day", APR, 6)

        # Labour Day
        self._add_labor_day("Labour Day")

        # Ascension Day
        self._add_ascension_thursday("Ascension Day")

        # President Nkurunziza Day
        if year >= 2022:
            self._add_holiday("President Nkurunziza Day", JUN, 8)

        # Independence Day
        self._add_holiday("Independence Day", JUL, 1)

        # Assumption Day
        self._add_assumption_of_mary_day("Assumption Day")

        # Prince Louis Rwagasore Day
        self._add_holiday("Prince Louis Rwagasore Day", OCT, 13)

        # President Ndadaye's Day
        if year >= 1994:
            self._add_holiday("President Ndadaye's Day", OCT, 21)

        # All Saints' Day
        self._add_all_saints_day("All Saints' Day")

        # Christmas Day
        self._add_christmas_day("Christmas Day")

        # Eid ul Fitr
        # date of observance is announced yearly
        self._add_eid_al_fitr_day("Eid ul Fitr")

        # Eid al Adha
        # date of observance is announced yearly
        self._add_eid_al_adha_day("Eid al Adha")


class BI(Burundi):
    pass


class BDI(Burundi):
    pass
