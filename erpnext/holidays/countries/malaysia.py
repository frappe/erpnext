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

from holidays.calendars import (
    _CustomBuddhistCalendar,
    _CustomChineseCalendar,
    _CustomHinduCalendar,
    _CustomIslamicCalendar,
)
from holidays.calendars.gregorian import (
    JAN,
    FEB,
    MAR,
    APR,
    MAY,
    JUN,
    JUL,
    AUG,
    SEP,
    OCT,
    NOV,
    DEC,
    MON,
    FRI,
    SAT,
    SUN,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import (
    BuddhistCalendarHolidays,
    ChineseCalendarHolidays,
    ChristianHolidays,
    HinduCalendarHolidays,
    InternationalHolidays,
    IslamicHolidays,
)


class Malaysia(
    HolidayBase,
    BuddhistCalendarHolidays,
    ChineseCalendarHolidays,
    ChristianHolidays,
    HinduCalendarHolidays,
    InternationalHolidays,
    IslamicHolidays,
):
    country = "MY"
    special_holidays = {
        # The years 1955 1959 1995 seems to have the elections
        # one weekday but I am not sure if they were marked as
        # holidays.
        1999: (NOV, 29, "Malaysia General Election Holiday"),
        2018: (MAY, 9, "Malaysia General Election Holiday"),
        2019: (JUL, 30, "Installation of New King"),
    }
    subdivisions = (
        "JHR",
        "KDH",
        "KTN",
        "KUL",
        "LBN",
        "MLK",
        "NSN",
        "PHG",
        "PJY",
        "PLS",
        "PNG",
        "PRK",
        "SBH",
        "SGR",
        "SWK",
        "TRG",
    )

    def __init__(self, *args, **kwargs) -> None:
        """
        An subclass of :py:class:`HolidayBase` representing public holidays in
        Malaysia.

        If ``subdiv`` for a state is not supplied, only nationwide holidays are
        returned. The following ``subdiv`` state codes are used (ISO 3166-2
        subdivision codes are not yet supported):

        - JHR: Johor
        - KDH: Kedah
        - KTN: Kelantan
        - MLK: Melaka
        - NSN: Negeri Sembilan
        - PHG: Pahang
        - PRK: Perak
        - PLS: Perlis
        - PNG: Pulau Pinang
        - SBH: Sabah
        - SWK: Sarawak
        - SGR: Selangor
        - TRG: Terengganu
        - KUL: FT Kuala Lumpur
        - LBN: FT Labuan
        - PJY: FT Putrajaya

        Limitations:

        - Prior to 2021: holidays are not accurate.
        - 2027 and later: Thaipusam dates are are estimated, and so denoted.

        Reference: `Wikipedia
        <https://en.wikipedia.org/wiki/Public_holidays_in_Malaysia>`__

        Country created by: `Eden <https://github.com/jusce17>`__

        Country maintained by: `Mike Borsetti <https://github.com/mborsetti>`__

        See parameters and usage in :py:class:`HolidayBase`.
        """
        BuddhistCalendarHolidays.__init__(
            self, calendar=MalaysiaBuddhistCalendar(), show_estimated=True
        )
        ChineseCalendarHolidays.__init__(
            self, calendar=MalaysiaChineseCalendar(), show_estimated=True
        )
        ChristianHolidays.__init__(self)
        HinduCalendarHolidays.__init__(self, calendar=MalaysiaHinduCalendar())
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=MalaysiaIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)
        observed_dates = set()

        # Chinese New Year (one day in the States of Kelantan and Terengganu,
        # two days in the other States).
        observed_dates.add(self._add_chinese_new_years_day("Chinese New Year"))
        # The second day of Chinese New Year is not a federal holiday in
        # Kelantan and Terengganu. However, it is gazetted as a state holiday
        # in both states, effectively making it a nationwide holiday.
        observed_dates.add(self._add_chinese_new_years_day_two("Chinese New Year Holiday"))

        # Vesak Day.
        observed_dates.add(self._add_vesak_may("Vesak Day"))

        # Labour Day.
        observed_dates.add(self._add_labor_day("Labour Day"))

        # Birthday of [His Majesty] the Yang di-Pertuan Agong.
        if year <= 2017:
            hol_date = self._get_nth_weekday_of_month(1, SAT, JUN)
        elif year == 2018:
            hol_date = date(2018, SEP, 9)
        elif year == 2020:
            # https://www.nst.com.my/news/nation/2020/03/571660/agongs-birthday-moved-june-6-june-8
            hol_date = date(2020, JUN, 8)
        else:
            hol_date = self._get_nth_weekday_of_month(1, MON, JUN)
        observed_dates.add(self._add_holiday("Birthday of SPB Yang di-Pertuan Agong", hol_date))

        # Hari Kebangsaan or National Day.
        observed_dates.add(self._add_holiday("National Day", AUG, 31))

        # Malaysia Day.
        if year >= 2010:
            observed_dates.add(self._add_holiday("Malaysia Day", SEP, 16))

        # Deepavali (Diwali).
        if self.subdiv != "SWK":
            observed_dates.add(self._add_diwali("Deepavali"))

        # Christmas day.
        observed_dates.add(self._add_christmas_day("Christmas Day"))

        # Birthday of the Prophet Muhammad (s.a.w.).
        # a.k.a. Hari Keputeraan Nabi Muhammad (Sabah Act)
        observed_dates.update(
            self._add_mawlid_day("Maulidur Rasul (Birthday of the Prophet Muhammad)")
        )

        # Hari Raya Puasa (2 days).
        # aka Eid al-Fitr;
        # exact date of observance is announced yearly
        name = "Hari Raya Puasa"
        observed_dates.update(self._add_eid_al_fitr_day(name))
        observed_dates.update(self._add_eid_al_fitr_day_two(f"Second day of {name}"))

        # Arafat Day.
        if self.subdiv == "TRG":
            observed_dates.update(self._add_arafah_day("Arafat Day"))

        # Hari Raya Haji.
        name = "Hari Raya Haji"
        observed_dates.update(self._add_eid_al_adha_day(name))
        if self.subdiv in {"KDH", "KTN", "PLS", "TRG"}:
            observed_dates.update(self._add_eid_al_adha_day_two(name))

        # New Year's Day
        if self.subdiv in {
            "KUL",
            "LBN",
            "MLK",
            "NSN",
            "PHG",
            "PJY",
            "PNG",
            "PRK",
            "SBH",
            "SGR",
            "SWK",
        }:
            observed_dates.add(self._add_new_years_day("New Year's Day"))

        # Isra and Mi'raj.
        if self.subdiv in {"KDH", "NSN", "PLS"} or (self.subdiv == "TRG" and year >= 2020):
            observed_dates.update(self._add_isra_and_miraj_day("Isra and Mi'raj"))

        # Beginning of Ramadan.
        if self.subdiv in {"JHR", "KDH", "MLK"}:
            observed_dates.update(self._add_ramadan_beginning_day("Beginning of Ramadan"))

        # Nuzul Al-Quran Day.
        if self.subdiv in {
            "KTN",
            "KUL",
            "LBN",
            "PHG",
            "PJY",
            "PLS",
            "PNG",
            "PRK",
            "SGR",
            "TRG",
        }:
            observed_dates.update(self._add_nuzul_al_quran_day("Nuzul Al-Quran Day"))

        # Thaipusam.
        if self.subdiv in {"JHR", "KUL", "NSN", "PJY", "PNG", "PRK", "SGR"}:
            observed_dates.add(self._add_thaipusam("Thaipusam"))

        # Federal Territory Day.
        if self.subdiv in {"KUL", "LBN", "PJY"} and year >= 1974:
            observed_dates.add(self._add_holiday("Federal Territory Day", FEB, 1))

        # State holidays (single state)

        if self.subdiv == "MLK":
            if year >= 1989:
                observed_dates.add(
                    self._add_holiday("Declaration of Malacca as a Historical City", APR, 15)
                )

            dt = (
                date(year, AUG, 24)
                if year >= 2020
                else self._get_nth_weekday_of_month(2, FRI, OCT)
            )
            observed_dates.add(self._add_holiday("Birthday of the Governor of Malacca", dt))

        elif self.subdiv == "NSN" and year >= 2009:
            observed_dates.add(
                self._add_holiday("Birthday of the Sultan of Negeri Sembilan", JAN, 14)
            )

        elif self.subdiv == "PHG" and year >= 1975:
            observed_dates.add(
                self._add_holiday("Hari Hol of Pahang", MAY, 22 if year >= 2021 else 7)
            )

            hol_date = (JUL, 30) if year >= 2019 else (OCT, 24)
            observed_dates.add(self._add_holiday("Birthday of the Sultan of Pahang", *hol_date))

        elif self.subdiv == "PNG":
            if year >= 2009:
                observed_dates.add(self._add_holiday("George Town Heritage Day", JUL, 7))

            observed_dates.add(
                self._add_holiday(
                    "Birthday of the Governor of Penang",
                    self._get_nth_weekday_of_month(2, SAT, JUL),
                )
            )

        elif self.subdiv == "PLS" and year >= 2000:
            hol_date = (JUL, 17) if year >= 2018 else (MAY, 17)
            observed_dates.add(self._add_holiday("Birthday of The Raja of Perlis", *hol_date))

        elif self.subdiv == "SGR":
            observed_dates.add(self._add_holiday("Birthday of The Sultan of Selangor", DEC, 11))

        elif self.subdiv == "SWK":
            # Dayak Festival Day (the first day of June) and the following day.
            observed_dates.add(self._add_holiday("Gawai Dayak", JUN, 1))
            observed_dates.add(self._add_holiday("Gawai Dayak (Second day)", JUN, 2))

            # Birthday of Tuan Yang Terutama Yang di-Pertua Negeri Sarawak
            # (the second Saturday of October).
            observed_dates.add(
                self._add_holiday(
                    "Birthday of the Governor of Sarawak",
                    self._get_nth_weekday_of_month(2, SAT, OCT),
                )
            )

            # Sarawak Independence Day
            if year >= 2017:
                observed_dates.add(self._add_holiday("Sarawak Day", JUL, 22))

        elif self.subdiv == "TRG" and year >= 2000:
            observed_dates.add(
                self._add_holiday(
                    "Anniversary of the Installation of the Sultan of Terengganu", MAR, 4
                )
            )

            observed_dates.add(self._add_holiday("Birthday of the Sultan of Terengganu", APR, 26))

        # Check for holidays that fall on a Sunday and
        # implement Section 3 of Malaysian Holidays Act:
        # "if any day specified in the Schedule falls on
        # Sunday then the day following shall be a public
        # holiday and if such day is already a public holiday,
        # then the day following shall be a public holiday"
        # In Johor and Kedah it's Friday -> Sunday,
        # in Kelantan and Terengganu it's Saturday -> Sunday
        if self.observed:
            weekday_observed_days = (
                (FRI, +2)
                if self.subdiv in {"JHR", "KDH"}
                else ((SAT, +1) if self.subdiv in {"KTN", "TRG"} else (SUN, +1))
            )
            observed_dates.difference_update({None})
            for hol_date in sorted(observed_dates):
                if hol_date.weekday() != weekday_observed_days[0]:
                    continue
                in_lieu_date = hol_date + td(days=weekday_observed_days[1])
                while in_lieu_date in observed_dates:
                    in_lieu_date += td(days=+1)
                for hol_name in self.get_list(hol_date):
                    self._add_holiday(f"{hol_name} [In lieu]", in_lieu_date)
                observed_dates.add(in_lieu_date)

            # special cases (observed from previuos year)
            if year == 2007 and self.subdiv not in {
                "JHR",
                "KDH",
                "KTN",
                "TRG",
            }:
                self._add_holiday("Hari Raya Haji [In lieu]", JAN, 2)

            if year == 2007 and self.subdiv == "TRG":
                self._add_holiday("Arafat Day [In lieu]", JAN, 2)

        # The last two days in May (Pesta Kaamatan).
        # (Sarawak Act)
        # Day following a Sunday is not a holiday
        if self.subdiv in {"LBN", "SBH"}:
            self._add_holiday("Pesta Kaamatan", MAY, 30)
            self._add_holiday("Pesta Kaamatan (Second day)", MAY, 31)

        # Other holidays (decrees etc.)

        # Awal Muharram.
        self._add_islamic_new_year_day("Awal Muharram (Hijri New Year)")

        # Special holidays (states)
        if year == 2021 and self.subdiv in {"KUL", "LBN", "PJY"}:
            self._add_holiday("Malaysia Cup Holiday", DEC, 3)

        if year == 2022 and self.subdiv == "KDH":
            self._add_holiday("Thaipusam", JAN, 18)

        if year == 2022 and self.subdiv in {"JHR", "KDH", "KTN", "TRG"}:
            self._add_holiday("Labour Day Holiday", MAY, 4)

        # Multiple state holidays.
        # Good Friday.
        if self.subdiv in {"SBH", "SWK"}:
            self._add_good_friday("Good Friday")

        # Single state holidays.
        if self.subdiv == "JHR":
            if year >= 2015:
                self._add_holiday("Birthday of the Sultan of Johor", MAR, 23)

            if year >= 2011:
                self._add_hari_hol_johor("Hari Hol of Sultan Iskandar of Johor")

        elif self.subdiv == "KDH" and year >= 2020:
            self._add_holiday(
                "Birthday of The Sultan of Kedah", self._get_nth_weekday_of_month(3, SUN, JUN)
            )

        elif self.subdiv == "KTN" and year >= 2010:
            name = "Birthday of the Sultan of Kelantan"
            self._add_holiday(name, NOV, 11)
            self._add_holiday(name, NOV, 12)

        elif self.subdiv == "PRK":
            # This Holiday used to be on 27th until 2017
            # https://www.officeholidays.com/holidays/malaysia/birthday-of-the-sultan-of-perak
            dt = (
                self._get_nth_weekday_of_month(1, FRI, NOV)
                if year >= 2018
                else date(year, NOV, 27)
            )
            self._add_holiday("Birthday of the Sultan of Perak", dt)

        elif self.subdiv == "SBH":
            self._add_holiday(
                "Birthday of the Governor of Sabah", self._get_nth_weekday_of_month(1, SAT, OCT)
            )

            if year >= 2019:
                self._add_christmas_eve("Christmas Eve")


class MY(Malaysia):
    pass


class MYS(Malaysia):
    pass


class MalaysiaBuddhistCalendar(_CustomBuddhistCalendar):
    VESAK_MAY_DATES = {
        2001: (MAY, 7),
        2002: (MAY, 27),
        2003: (MAY, 15),
        2004: (MAY, 3),
        2005: (MAY, 22),
        2006: (MAY, 12),
        2007: (MAY, 1),
        2008: (MAY, 19),
        2009: (MAY, 9),
        2010: (MAY, 28),
        2011: (MAY, 17),
        2012: (MAY, 5),
        2013: (MAY, 24),
        2014: (MAY, 13),
        2015: (MAY, 3),
        2016: (MAY, 21),
        2017: (MAY, 10),
        2018: (MAY, 29),
        2019: (MAY, 19),
        2020: (MAY, 7),
        2021: (MAY, 26),
        2022: (MAY, 15),
        2023: (MAY, 4),
    }


class MalaysiaChineseCalendar(_CustomChineseCalendar):
    LUNAR_NEW_YEAR_DATES = {
        2001: (JAN, 24),
        2002: (FEB, 12),
        2003: (FEB, 1),
        2004: (JAN, 22),
        2005: (FEB, 9),
        2006: (JAN, 29),
        2007: (FEB, 18),
        2008: (FEB, 7),
        2009: (JAN, 26),
        2010: (FEB, 14),
        2011: (FEB, 3),
        2012: (JAN, 23),
        2013: (FEB, 10),
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


class MalaysiaHinduCalendar(_CustomHinduCalendar):
    DIWALI_DATES = {
        2001: (NOV, 14),
        2002: (NOV, 3),
        2003: (OCT, 23),
        2004: (NOV, 11),
        2005: (NOV, 1),
        2006: (OCT, 21),
        2007: (NOV, 8),
        2008: (OCT, 27),
        2009: (OCT, 17),
        2010: (NOV, 5),
        2011: (OCT, 26),
        2012: (NOV, 13),
        2013: (NOV, 2),
        2014: (OCT, 22),
        2015: (NOV, 10),
        2016: (OCT, 29),
        2017: (OCT, 18),
        2018: (NOV, 6),
        2019: (OCT, 27),
        2020: (NOV, 14),
        2021: (NOV, 4),
        2022: (OCT, 24),
        2023: (NOV, 12),
    }

    THAIPUSAM_DATES = {
        2018: (JAN, 31),
        2019: (JAN, 21),
        2020: (FEB, 8),
        2021: (JAN, 28),
        2022: (JAN, 18),
        2023: (FEB, 5),
        2024: (JAN, 25),
        2025: (FEB, 11),
        2026: (FEB, 1),
        2027: (JAN, 22),
    }


class MalaysiaIslamicCalendar(_CustomIslamicCalendar):
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
        2001: (DEC, 17),
        2002: (DEC, 6),
        2003: (NOV, 26),
        2004: (NOV, 14),
        2005: (NOV, 3),
        2006: (OCT, 24),
        2007: (OCT, 13),
        2008: (OCT, 1),
        2009: (SEP, 20),
        2010: (SEP, 10),
        2011: (AUG, 31),
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

    HARI_HOL_JOHOR_DATES = {
        2011: (JAN, 12),
        2012: ((JAN, 1), (DEC, 20)),
        2013: (DEC, 10),
        2014: (NOV, 29),
        2015: (NOV, 19),
        2016: (NOV, 7),
        2017: (OCT, 27),
        2018: (OCT, 15),
        2019: (OCT, 5),
        2020: (SEP, 24),
        2021: (SEP, 13),
        2022: (SEP, 3),
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
        2010: (DEC, 8),
        2011: (NOV, 27),
        2012: (NOV, 15),
        2013: (NOV, 5),
        2014: (OCT, 25),
        2015: (OCT, 14),
        2016: (OCT, 2),
        2017: (SEP, 22),
        2018: (SEP, 11),
        2019: (SEP, 1),
        2020: (AUG, 20),
        2021: (AUG, 10),
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
        2016: (MAY, 5),
        2017: (APR, 24),
        2018: (APR, 14),
        2019: (APR, 3),
        2020: (MAR, 22),
        2021: (MAR, 11),
        2022: (MAR, 1),
        2023: (FEB, 18),
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
        2018: (NOV, 20),
        2019: (NOV, 9),
        2020: (OCT, 29),
        2021: (OCT, 19),
        2022: (OCT, 10),
    }
    NUZUL_AL_QURAN_DATES = {
        2001: (DEC, 3),
        2002: (NOV, 22),
        2003: (NOV, 12),
        2004: (NOV, 1),
        2005: (OCT, 21),
        2006: (OCT, 10),
        2007: (SEP, 29),
        2008: (SEP, 18),
        2009: (SEP, 7),
        2010: (AUG, 27),
        2011: (AUG, 17),
        2012: (AUG, 5),
        2013: (JUL, 25),
        2014: (JUL, 15),
        2015: (JUL, 4),
        2016: (JUN, 22),
        2017: (JUN, 12),
        2018: (JUN, 2),
        2019: (MAY, 22),
        2020: (MAY, 10),
        2021: (APR, 29),
        2022: (APR, 19),
        2023: (APR, 8),
    }

    RAMADAN_BEGINNING_DATES = {
        2001: (NOV, 17),
        2002: (NOV, 6),
        2003: (OCT, 27),
        2004: (OCT, 16),
        2005: (OCT, 5),
        2006: (SEP, 24),
        2007: (SEP, 13),
        2008: (SEP, 2),
        2009: (AUG, 22),
        2010: (AUG, 11),
        2011: (AUG, 1),
        2012: (JUL, 20),
        2013: (JUL, 9),
        2014: (JUN, 29),
        2015: (JUN, 18),
        2016: (JUN, 7),
        2017: (MAY, 27),
        2018: (MAY, 17),
        2019: (MAY, 6),
        2020: (APR, 24),
        2021: (APR, 13),
        2022: (APR, 3),
        2023: (MAR, 23),
    }
