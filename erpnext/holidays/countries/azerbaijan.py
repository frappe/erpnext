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

from holidays.calendars import _CustomIslamicCalendar
from holidays.calendars.gregorian import JAN, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import InternationalHolidays, IslamicHolidays


class Azerbaijan(HolidayBase, InternationalHolidays, IslamicHolidays):
    # [1] https://en.wikipedia.org/wiki/Public_holidays_in_Azerbaijan
    # [2] https://az.wikipedia.org/wiki/Az%C9%99rbaycan%C4%B1n_d%C3%B6vl%C9%99t_bayramlar%C4%B1_v%C9%99_x%C3%BCsusi_g%C3%BCnl%C9%99ri  # noqa: E501
    # [3] https://www.sosial.gov.az/en/prod-calendar

    country = "AZ"

    def __init__(self, *args, **kwargs):
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=AzerbaijanIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        def _add_observed(dt: date, name: str = None):
            """
            Add observed holiday on next working day after specified date.
            """

            next_workday = dt + td(days=+1)
            while next_workday in hol_dates or self._is_weekend(next_workday):
                next_workday += td(days=+1)
            if name:
                self._add_holiday(f"{name} (Observed)", next_workday)
            else:
                for h_name in self.get_list(dt):
                    self._add_holiday(f"{h_name} (Observed)", next_workday)
            hol_dates.add(next_workday)

        if year <= 1989:
            return None

        super()._populate(year)
        observed_dates = set()
        non_observed_dates = set()

        # New Year
        name = "New Year's Day"
        observed_dates.add(self._add_new_years_day(name))
        if year >= 2006:
            observed_dates.add(self._add_new_years_day_two(name))

        # Black January (without extending)
        if year >= 2000:
            non_observed_dates.add(self._add_holiday("Black January", JAN, 20))

        # International Women's Day
        observed_dates.add(self._add_womens_day("International Women's Day"))

        # Novruz
        if year >= 2007:
            for d in range(20, 25):
                observed_dates.add(self._add_holiday("Novruz", MAR, d))

        # Victory Day
        observed_dates.add(self._add_world_war_two_victory_day("Victory Day over Fascism"))

        # Republic Day
        if year >= 1992:
            observed_dates.add(
                self._add_holiday("Independence Day" if year >= 2021 else "Republic Day", MAY, 28)
            )

        # National Salvation Day
        if year >= 1997:
            observed_dates.add(self._add_holiday("National Salvation Day", JUN, 15))

        # Memorial Day (without extending)
        if year >= 2021:
            non_observed_dates.add(self._add_holiday("Memorial Day", SEP, 27))

        # Azerbaijan Armed Forces Day
        if year >= 1992:
            name = "Azerbaijan Armed Forces Day"
            if year <= 1997:
                self._add_holiday(name, OCT, 9)
            else:
                observed_dates.add(self._add_holiday(name, JUN, 26))

        # Independence Day
        if year <= 2005:
            self._add_holiday("Independence Day", OCT, 18)

        # Victory Day
        if year >= 2021:
            observed_dates.add(self._add_holiday("Victory Day", NOV, 8))

        # Flag Day
        if year >= 2010:
            observed_dates.add(self._add_holiday("Flag Day", NOV, 9))

        # International Solidarity Day of Azerbaijanis
        if year >= 1993:
            solidarity_name = "International Solidarity Day of Azerbaijanis"
            self._add_new_years_eve(solidarity_name)

        if year >= 1993:
            name = "Ramazan Bayrami"
            observed_dates.update(self._add_eid_al_fitr_day(name))
            observed_dates.update(self._add_eid_al_fitr_day_two(name))

            name = "Gurban Bayrami"
            observed_dates.update(self._add_eid_al_adha_day(name))
            observed_dates.update(self._add_eid_al_adha_day_two(name))

        # Article 105 of the Labor Code of the Republic of Azerbaijan states:
        # 5. If interweekly rest days and holidays that are not considered
        # working days overlap, that rest day is immediately transferred to
        # the next working day.
        if self.observed and year >= 2006:
            hol_dates = observed_dates.union(non_observed_dates)

            dt = date(year - 1, DEC, 31)
            if self._is_weekend(dt):
                _add_observed(dt, solidarity_name)

            # observed holidays special cases
            special_dates_obs = {2007: (JAN, 3), 2072: (JAN, 5)}
            if year in special_dates_obs:
                hol_dates.add(
                    self._add_holiday(
                        "Gurban Bayrami* (*estimated) (Observed)", *special_dates_obs[year]
                    )
                )

            for hol_date in sorted(observed_dates):
                if self._is_weekend(hol_date):
                    _add_observed(hol_date)

                # 6. If the holidays of Qurban and Ramadan coincide with
                # another holiday that is not considered a working day,
                # the next working day is considered a rest day.
                elif len(self.get_list(hol_date)) > 1 and hol_date not in non_observed_dates:
                    for hol_name in self.get_list(hol_date):
                        if "Bayrami" in hol_name:
                            _add_observed(hol_date, hol_name)


class AZ(Azerbaijan):
    pass


class AZE(Azerbaijan):
    pass


class AzerbaijanIslamicCalendar(_CustomIslamicCalendar):
    EID_AL_ADHA_DATES = {
        2011: (NOV, 6),
        2012: (OCT, 25),
        2013: (OCT, 15),
        2014: (OCT, 4),
        2015: (SEP, 24),
        2016: (SEP, 12),
        2017: (SEP, 1),
        2018: (AUG, 22),
        2019: (AUG, 12),
        2020: (JUL, 31),
        2021: (JUL, 20),
        2022: (JUL, 9),
        2023: (JUN, 28),
    }

    EID_AL_FITR_DATES = {
        2011: (AUG, 30),
        2012: (AUG, 19),
        2013: (AUG, 8),
        2014: (JUL, 28),
        2015: (JUL, 17),
        2016: (JUL, 6),
        2017: (JUN, 26),
        2018: (JUN, 15),
        2019: (JUN, 5),
        2020: (MAY, 24),
        2021: (MAY, 13),
        2022: (MAY, 2),
        2023: (APR, 21),
    }
