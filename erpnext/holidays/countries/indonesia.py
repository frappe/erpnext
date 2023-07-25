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

from holidays.calendars import (
    _CustomBuddhistCalendar,
    _CustomChineseCalendar,
    _CustomIslamicCalendar,
)
from holidays.calendars.gregorian import JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import (
    BuddhistCalendarHolidays,
    ChineseCalendarHolidays,
    ChristianHolidays,
    InternationalHolidays,
    IslamicHolidays,
)


class Indonesia(
    HolidayBase,
    BuddhistCalendarHolidays,
    ChineseCalendarHolidays,
    ChristianHolidays,
    InternationalHolidays,
    IslamicHolidays,
):
    """
    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Indonesia
    - https://www.timeanddate.com/holidays/indonesia
    - https://www.officeholidays.com/countries/indonesia
    """

    country = "ID"
    special_holidays = {
        # Election Day.
        2018: (JUN, 27, "Hari Pemilihan"),
        2019: (APR, 17, "Hari Pemilihan"),
        2020: (DEC, 9, "Hari Pemilihan"),
    }

    def __init__(self, *args, **kwargs):
        BuddhistCalendarHolidays.__init__(
            self, calendar=IndonesiaBuddhistCalendar(), show_estimated=True
        )
        ChineseCalendarHolidays.__init__(
            self, calendar=IndonesiaChineseCalendar(), show_estimated=True
        )
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=IndonesiaIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("Tahun Baru Masehi")

        if year >= 2003:
            # Chinese New Year.
            self._add_chinese_new_years_day("Tahun Baru Imlek")

        if year >= 1983:
            # https://en.wikipedia.org/wiki/Nyepi
            dates_obs = {
                2009: (MAR, 26),
                2010: (MAR, 16),
                2011: (MAR, 5),
                2012: (MAR, 23),
                2013: (MAR, 12),
                2014: (MAR, 31),
                2015: (MAR, 21),
                2016: (MAR, 9),
                2017: (MAR, 28),
                2018: (MAR, 17),
                2019: (MAR, 7),
                2020: (MAR, 25),
                2021: (MAR, 14),
                2022: (MAR, 3),
                2023: (MAR, 22),
                2024: (MAR, 11),
                2025: (MAR, 29),
                2026: (MAR, 19),
            }
            if year in dates_obs:
                # Day of Silence.
                self._add_holiday("Hari Suci Nyepi", *dates_obs[year])

        # Eid al-Fitr.
        self._add_eid_al_fitr_day("Hari Raya Idul Fitri")
        self._add_eid_al_fitr_day_two("Hari kedua dari Hari Raya Idul Fitri")

        # Eid al-Adha.
        self._add_eid_al_adha_day("Hari Raya Idul Adha")

        # Islamic New Year.
        self._add_islamic_new_year_day("Tahun Baru Islam")

        # The Prophet's Birthday.
        self._add_mawlid_day("Maulid Nabi Muhammad")

        # The Prophet's Ascension.
        self._add_isra_and_miraj_day("Isra' Mi'raj Nabi Muhammad")

        # Good Friday.
        self._add_good_friday("Wafat Yesus Kristus")

        if year >= 1983:
            # Buddha's Birthday.
            self._add_vesak("Hari Raya Waisak")

        if 1953 <= year <= 1968 or year >= 2014:
            # Labor Day.
            self._add_labor_day("Hari Buruh Internasional")

        # Ascension Day.
        self._add_ascension_thursday("Kenaikan Yesus Kristus")

        if year >= 2017:
            # Pancasila Day.
            self._add_holiday("Hari Lahir Pancasila", JUN, 1)

        # Independence Day.
        self._add_holiday("Hari Kemerdekaan Republik Indonesia", AUG, 17)

        # Christmas Day.
        self._add_christmas_day("Hari Raya Natal")


class ID(Indonesia):
    pass


class IDN(Indonesia):
    pass


class IndonesiaBuddhistCalendar(_CustomBuddhistCalendar):
    VESAK_DATES = {
        2007: (JUN, 1),
        2008: (MAY, 20),
        2009: (MAY, 9),
        2010: (MAY, 28),
        2011: (MAY, 17),
        2012: (MAY, 6),
        2013: (MAY, 25),
        2014: (MAY, 15),
        2015: (JUN, 2),
        2016: (MAY, 22),
        2017: (MAY, 11),
        2018: (MAY, 29),
        2019: (MAY, 19),
        2020: (MAY, 7),
        2021: (MAY, 26),
        2022: (MAY, 16),
        2023: (JUN, 4),
    }


class IndonesiaChineseCalendar(_CustomChineseCalendar):
    LUNAR_NEW_YEAR_DATES = {
        2003: (FEB, 1),
        2004: (JAN, 22),
        2005: (FEB, 9),
        2006: (JAN, 30),
        2007: (FEB, 19),
        2008: (FEB, 7),
        2009: (JAN, 26),
        2010: (FEB, 15),
        2011: (FEB, 3),
        2012: (JAN, 23),
        2013: (FEB, 11),
        2014: (JAN, 31),
        2015: (FEB, 19),
        2016: (FEB, 8),
        2017: (JAN, 28),
        2018: (FEB, 16),
        2019: (FEB, 5),
        2020: (JAN, 25),
        2021: (FEB, 12),
        2022: (FEB, 1),
        2023: (JAN, 22),
    }


class IndonesiaIslamicCalendar(_CustomIslamicCalendar):
    EID_AL_ADHA_DATES = {
        2001: (MAR, 6),
        2002: (FEB, 23),
        2003: (FEB, 12),
        2004: (FEB, 2),
        2005: (JAN, 21),
        2006: ((JAN, 10), (DEC, 31)),
        2007: (DEC, 20),
        2008: (DEC, 8),
        2009: (NOV, 27),
        2010: (NOV, 17),
        2011: (NOV, 6),
        2012: (OCT, 26),
        2013: (OCT, 15),
        2014: (OCT, 5),
        2015: (SEP, 24),
        2016: (SEP, 12),
        2017: (SEP, 1),
        2018: (AUG, 22),
        2019: (AUG, 11),
        2020: (JUL, 31),
        2021: (JUL, 20),
        2022: (JUL, 10),
        2023: (JUN, 29),
    }

    EID_AL_FITR_DATES = {
        2001: (DEC, 16),
        2002: (DEC, 6),
        2003: (NOV, 25),
        2004: (NOV, 14),
        2005: (NOV, 3),
        2006: (OCT, 24),
        2007: (OCT, 13),
        2008: (OCT, 1),
        2009: (SEP, 20),
        2010: (SEP, 10),
        2011: (AUG, 30),
        2012: (AUG, 19),
        2013: (AUG, 8),
        2014: (JUL, 28),
        2015: (JUL, 17),
        2016: (JUL, 6),
        2017: (JUN, 25),
        2018: (JUN, 15),
        2019: (JUN, 5),
        2020: (MAY, 24),
        2021: (MAY, 13),
        2022: (MAY, 2),
        2023: (APR, 22),
    }

    HIJRI_NEW_YEAR_DATES = {
        2001: (MAR, 26),
        2002: (MAR, 15),
        2003: (MAR, 5),
        2004: (FEB, 22),
        2005: (FEB, 10),
        2006: (JAN, 31),
        2007: (JAN, 20),
        2008: ((JAN, 10), (DEC, 29)),
        2009: (DEC, 18),
        2010: (DEC, 7),
        2011: (NOV, 27),
        2012: (NOV, 15),
        2013: (NOV, 5),
        2014: (OCT, 25),
        2015: (OCT, 14),
        2016: (OCT, 2),
        2017: (SEP, 21),
        2018: (SEP, 11),
        2019: (SEP, 1),
        2020: (AUG, 20),
        2021: (AUG, 11),
        2022: (JUL, 30),
    }

    ISRA_AND_MIRAJ_DATES = {
        2001: (OCT, 15),
        2002: (OCT, 4),
        2003: (SEP, 24),
        2004: (SEP, 12),
        2005: (SEP, 1),
        2006: (AUG, 22),
        2007: (AUG, 11),
        2008: (JUL, 31),
        2009: (JUL, 20),
        2010: (JUL, 9),
        2011: (JUN, 29),
        2012: (JUN, 17),
        2013: (JUN, 6),
        2014: (MAY, 27),
        2015: (MAY, 16),
        2016: (MAY, 6),
        2017: (APR, 24),
        2018: (APR, 14),
        2019: (APR, 3),
        2020: (MAR, 22),
        2021: (MAR, 11),
        2022: (FEB, 28),
    }

    MAWLID_DATES = {
        2006: (APR, 10),
        2007: (MAR, 31),
        2008: (MAR, 20),
        2009: (MAR, 9),
        2010: (FEB, 26),
        2011: (FEB, 15),
        2012: (FEB, 5),
        2013: (JAN, 24),
        2014: (JAN, 14),
        2015: ((JAN, 3), (DEC, 24)),
        2016: (DEC, 12),
        2017: (DEC, 1),
        2018: (NOV, 20),
        2019: (NOV, 9),
        2020: (OCT, 29),
        2021: (OCT, 19),
        2022: (OCT, 8),
    }
