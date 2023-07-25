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

from holidays.calendars.gregorian import FEB, MAR, APR, MAY, AUG, NOV
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Kyrgyzstan(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    Kyrgyzstan holidays.

    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Kyrgyzstan
    """

    country = "KG"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Orthodox Christmas.
        self._add_christmas_day("Christmas Day")

        # Feb. 23 Fatherland Defender's Day.
        self._add_holiday("Fatherland Defender's Day", FEB, 23)

        # International Women's Day.
        self._add_womens_day("International Women's Day")

        # Nooruz Mairamy.
        self._add_holiday("Nooruz Mairamy", MAR, 21)

        if year >= 2016:
            # Day of the People's April Revolution.
            self._add_holiday("Day of the People's April Revolution", APR, 7)

        # International Workers' Day.
        self._add_labor_day("International Workers' Day")

        # Constitution Day.
        self._add_holiday("Constitution Day", MAY, 5)

        # Victory Day.
        self._add_world_war_two_victory_day("Victory Day")

        # Independence Day.
        self._add_holiday("Independence Day", AUG, 31)

        # Days History and Commemoration of Ancestors.
        name = "Days of History and Commemoration of Ancestors"
        self._add_holiday(name, NOV, 7)
        self._add_holiday(name, NOV, 8)

        # New Year's Eve.
        self._add_new_years_eve("New Year's Eve")

        # Islamic Holidays.
        # Orozo Ait.
        name = "Orozo Ait"
        self._add_eid_al_fitr_day(name)
        self._add_eid_al_fitr_day_two(name)

        # Kurman Ait.
        self._add_eid_al_adha_day("Kurman Ait")


class KG(Kyrgyzstan):
    pass


class KGZ(Kyrgyzstan):
    pass
