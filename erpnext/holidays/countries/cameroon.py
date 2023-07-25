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

from holidays.calendars import _CustomIslamicCalendar
from holidays.calendars.gregorian import JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays, IslamicHolidays


class Cameroon(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Cameroon
      - https://www.timeanddate.com/holidays/cameroon
      - https://www.officeholidays.com/countries/cameroon
    """

    country = "CM"
    special_holidays = {
        2021: (
            (MAY, 14, "Public Holiday"),
            (JUL, 19, "Public Holiday"),
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=CameroonIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # On 1 January 1960, French Cameroun gained independence from France.
        if year <= 1959:
            return None

        super()._populate(year)
        observed_dates = set()

        # New Year's Day.
        observed_dates.add(self._add_new_years_day("New Year's Day"))

        # Youth Day.
        if year >= 1966:
            observed_dates.add(self._add_holiday("Youth Day", FEB, 11))

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Labour Day.
        observed_dates.add(self._add_labor_day("Labour Day"))

        # National Day.
        if year >= 1972:
            observed_dates.add(self._add_holiday("National Day", MAY, 20))

        # Ascension Day.
        self._add_ascension_thursday("Ascension Day")

        # Assumption Day.
        observed_dates.add(self._add_assumption_of_mary_day("Assumption Day"))

        # Christmas Day.
        observed_dates.add(self._add_christmas_day("Christmas Day"))

        # Eid al-Fitr.
        observed_dates.update(self._add_eid_al_fitr_day("Eid al-Fitr"))

        # Eid al-Adha.
        observed_dates.update(self._add_eid_al_adha_day("Eid al-Adha"))

        # Mawlid.
        observed_dates.update(self._add_mawlid_day("Mawlid"))

        if self.observed:
            for dt in sorted(observed_dates):
                if not self._is_sunday(dt):
                    continue
                obs_date = dt + td(days=+1)
                while obs_date in observed_dates:
                    obs_date += td(days=+1)
                for hol_name in self.get_list(dt):
                    observed_dates.add(self._add_holiday("%s (Observed)" % hol_name, obs_date))

            # observed holidays special cases
            if year == 2007:
                self._add_holiday("Eid al-Adha (Observed)", JAN, 2)


class CM(Cameroon):
    pass


class CMR(Cameroon):
    pass


class CameroonIslamicCalendar(_CustomIslamicCalendar):
    EID_AL_ADHA_DATES = {
        2001: (MAR, 6),
        2002: (FEB, 23),
        2003: (FEB, 12),
        2004: (FEB, 2),
        2005: (JAN, 21),
        2006: ((JAN, 10), (DEC, 31)),
        2007: (DEC, 20),
        2008: (DEC, 9),
        2009: (NOV, 28),
        2010: (NOV, 17),
        2011: (NOV, 7),
        2012: (OCT, 26),
        2013: (OCT, 15),
        2014: (OCT, 5),
        2015: (SEP, 24),
        2016: (SEP, 13),
        2017: (SEP, 2),
        2018: (AUG, 21),
        2019: (AUG, 11),
        2020: (JUL, 31),
        2021: (JUL, 20),
        2022: (JUL, 9),
        2023: (JUN, 28),
    }

    EID_AL_FITR_DATES = {
        2001: (DEC, 17),
        2002: (DEC, 6),
        2003: (NOV, 26),
        2004: (NOV, 14),
        2005: (NOV, 4),
        2006: (OCT, 24),
        2007: (OCT, 13),
        2008: (OCT, 2),
        2009: (SEP, 21),
        2010: (SEP, 10),
        2011: (AUG, 31),
        2012: (AUG, 19),
        2013: (AUG, 8),
        2014: (JUL, 28),
        2015: (JUL, 18),
        2016: (JUL, 7),
        2017: (JUN, 26),
        2018: (JUN, 15),
        2019: (JUN, 4),
        2020: (MAY, 24),
        2021: (MAY, 13),
        2022: (MAY, 2),
        2023: (APR, 21),
    }

    MAWLID_DATES = {
        2001: (JUN, 4),
        2002: (MAY, 24),
        2003: (MAY, 14),
        2004: (MAY, 2),
        2005: (APR, 21),
        2006: (APR, 11),
        2007: (MAR, 31),
        2008: (MAR, 20),
        2009: (MAR, 9),
        2010: (FEB, 26),
        2011: (FEB, 16),
        2012: (FEB, 5),
        2013: (JAN, 24),
        2014: (JAN, 14),
        2015: ((JAN, 3), (DEC, 24)),
        2016: (DEC, 12),
        2017: (DEC, 1),
        2018: (NOV, 21),
        2019: (NOV, 10),
        2020: (OCT, 29),
        2021: (OCT, 19),
        2022: (OCT, 8),
    }
