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

from holidays.calendars.gregorian import MAR, MAY, JUL, AUG, OCT, DEC
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Kazakhstan(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    1. https://www.officeholidays.com/countries/kazakhstan/2020
    2. https://egov.kz/cms/en/articles/holidays-calend
    3. https://en.wikipedia.org/wiki/Public_holidays_in_Kazakhstan
    4. https://adilet.zan.kz/rus/docs/Z010000267_/history
    """

    country = "KZ"

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # Kazakhstan declared its sovereignty on 25 October 1990
        if year <= 1990:
            return None

        super()._populate(year)
        observed_dates = set()

        # New Year's holiday (2 days)
        name = "New Year"
        observed_dates.add(self._add_new_years_day(name))
        observed_dates.add(self._add_new_years_day_two(name))

        # Orthodox Christmas (nonworking day, without extending)
        if year >= 2006:
            self._add_christmas_day("Orthodox Christmas")

        # International Women's Day
        observed_dates.add(self._add_womens_day("International Women's Day"))

        # Nauryz holiday
        if year >= 2002:
            name = "Nauryz holiday"
            observed_dates.add(self._add_holiday(name, MAR, 22))
            if year >= 2010:
                observed_dates.add(self._add_holiday(name, MAR, 21))
                observed_dates.add(self._add_holiday(name, MAR, 23))

        # Kazakhstan People Solidarity Holiday
        observed_dates.add(self._add_labor_day("Kazakhstan People Solidarity Holiday"))

        # Defender of the Fatherland Day
        if year >= 2013:
            observed_dates.add(self._add_holiday("Defender of the Fatherland Day", MAY, 7))

        # Victory Day
        observed_dates.add(self._add_world_war_two_victory_day("Victory Day"))

        # Capital Day
        if year >= 2009:
            observed_dates.add(self._add_holiday("Capital Day", JUL, 6))

        # Constitution Day of the Republic of Kazakhstan
        if year >= 1996:
            observed_dates.add(
                self._add_holiday("Constitution Day of the Republic of Kazakhstan", AUG, 30)
            )

        # Republic Day
        if 1994 <= year <= 2008 or year >= 2022:
            observed_dates.add(self._add_holiday("Republic Day", OCT, 25))

        # First President Day
        if 2012 <= year <= 2021:
            observed_dates.add(self._add_holiday("First President Day", DEC, 1))

        # Kazakhstan Independence Day
        name = "Kazakhstan Independence Day"
        observed_dates.add(self._add_holiday(name, DEC, 16))
        if 2002 <= year <= 2021:
            observed_dates.add(self._add_holiday(name, DEC, 17))

        # Kurban Ait (nonworking day, without extending)
        if year >= 2006:
            self._add_eid_al_adha_day("Kurban Ait")

        if self.observed and year >= 2002:
            for hol_date in sorted(observed_dates):
                if not self._is_weekend(hol_date):
                    continue
                obs_date = hol_date + td(days=+1)
                while self._is_weekend(obs_date) or obs_date in observed_dates:
                    obs_date += td(days=+1)
                observed_dates.add(self._add_holiday("%s (Observed)" % self[hol_date], obs_date))


class KZ(Kazakhstan):
    pass


class KAZ(Kazakhstan):
    pass
