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

from holidays.calendars.gregorian import JAN, MAR, SEP, OCT, NOV, DEC
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Albania(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Albania
    """

    country = "AL"
    special_holidays = {
        2022: (MAR, 21, "Public Holiday"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)
        observed_dates = set()

        # New Year's Day.
        name = "New Year's Day"
        observed_dates.add(self._add_new_years_day(name))
        observed_dates.add(self._add_new_years_day_two(name))

        # Summer Day.
        if year >= 2004:
            observed_dates.add(self._add_holiday("Summer Day", MAR, 14))

        # Nevruz.
        if year >= 1996:
            observed_dates.add(self._add_holiday("Nevruz", MAR, 22))

        # Easter.
        observed_dates.add(self._add_easter_sunday("Catholic Easter"))
        observed_dates.add(self._add_easter_sunday("Orthodox Easter", JULIAN_CALENDAR))

        # May Day.
        observed_dates.add(self._add_labor_day("May Day"))

        # Mother Teresa Day.
        if 2004 <= year <= 2017:
            observed_dates.add(self._add_holiday("Mother Teresa Beatification Day", OCT, 19))
        elif year >= 2018:
            observed_dates.add(self._add_holiday("Mother Teresa Canonization Day", SEP, 5))

        # Independence Day.
        observed_dates.add(self._add_holiday("Independence Day", NOV, 28))

        # Liberation Day.
        observed_dates.add(self._add_holiday("Liberation Day", NOV, 29))

        # National Youth Day.
        if year >= 2009:
            observed_dates.add(self._add_holiday("National Youth Day", DEC, 8))

        # Christmas Day.
        observed_dates.add(self._add_christmas_day("Christmas Day"))

        # Eid al-Fitr.
        observed_dates.update(self._add_eid_al_fitr_day("Eid al-Fitr"))

        # Eid al-Adha.
        observed_dates.update(self._add_eid_al_adha_day("Eid al-Adha"))

        if self.observed:
            for hol_date in sorted(observed_dates):
                if not self._is_weekend(hol_date):
                    continue
                obs_date = hol_date + td(days=+1)
                while self._is_weekend(obs_date) or obs_date in observed_dates:
                    obs_date += td(days=+1)
                for hol_name in self.get_list(hol_date):
                    observed_dates.add(self._add_holiday("%s (Observed)" % hol_name, obs_date))

            # observed holidays special cases
            if year == 2007:
                self._add_holiday("Eid al-Adha (Observed)", JAN, 3)


class AL(Albania):
    pass


class ALB(Albania):
    pass
