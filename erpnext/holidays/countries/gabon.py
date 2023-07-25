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

from holidays.calendars import _CustomIslamicCalendar
from holidays.calendars.gregorian import JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays, IslamicHolidays


class Gabon(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Gabon
      - https://www.timeanddate.com/holidays/gabon
      - https://www.officeholidays.com/countries/gabon
      - http://www.travail.gouv.ga/402-evenements/489-liste-des-jours-feries/
    """

    country = "GA"

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=GabonIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # On 17 August 1960, Gabon gained independence from France.
        if year <= 1960:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # Women's Rights Day.
        if year >= 2015:
            self._add_holiday("Women's Rights Day", APR, 17)

        # Labour Day.
        self._add_labor_day("Labour Day")

        # Ascension Day.
        self._add_ascension_thursday("Ascension Day")

        # Whit Monday.
        self._add_whit_monday("Whit Monday")

        # Assumption Day.
        self._add_assumption_of_mary_day("Assumption Day")

        # Independence Day.
        self._add_holiday("Independence Day", AUG, 16)
        self._add_holiday("Independence Day Holiday", AUG, 17)

        # All Saints' Day.
        self._add_all_saints_day("All Saints' Day")

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Eid al-Fitr.
        self._add_eid_al_fitr_day("Eid al-Fitr")

        # Eid al-Adha.
        self._add_eid_al_adha_day("Eid al-Adha")


class GA(Gabon):
    pass


class GAB(Gabon):
    pass


class GabonIslamicCalendar(_CustomIslamicCalendar):
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
        2018: (AUG, 22),
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
        2014: (JUL, 29),
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
