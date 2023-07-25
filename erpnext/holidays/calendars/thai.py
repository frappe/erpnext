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
from functools import lru_cache
from typing import Optional

KHMER_CALENDAR = "KHMER_CALENDAR"
THAI_CALENDAR = "THAI_CALENDAR"


class _ThaiLunisolar:
    """
    ** Thai Lunar Calendar Holidays only work from 1941 (B.E. 2484) onwards
       until 2057 (B.E. 2600) as we only have Thai year-type data for
       cross-checking until then.

    So here are the basics of the Thai Lunar Calendar
        3-year types for calendar intercalation:
            - Pakatimat (Normal Year):
                    consist of 12 months, has 354 days.
            - Athikawan (Extra-Day Year):
                    add a day to the 7th month of the year, has 355 days
                    for the synodic month correction.
            - Athikamat (Extra-Month Year):
                    we have the 8th month twice, has 384 days for the
                    sidereal year correction.

        Each month either has 30 (Even months) or 29 (Odd months)
            - The waxing phase has 15 days until Full Moon and waning
                phase 14 (Odd Months)/15 (Even Months/
                Month 7 of Athikawan years) days for the New Moon.
            - The second "Month 8" for Athikamat years is called
                "Month 8.8", with all observed holy days delayed from
                the usual calendar by 1 month.

    List of public holidays dependent on the Thai Lunar Calendar:
        - Magha Puja/Makha Bucha/Meak Bochea:
                15th Waxing Day (Full Moon) of Month 3
                (On Month 4 for Athikamat Years).
                KHMER_CALENDAR always fall on Month 3.
        - Vesak/Visakha Bucha/Visaka Bochea:
                15th Waxing Day (Full Moon) of Month 6
                (On Month 7 for Athikamat Years).
                KHMER_CALENDAR always fall on Month 6.
        - Thai Royal Ploughing Ceremony/Raeknakhwan:
                Based on this, though Court Astrologer picks the
                auspicious dates, which sadly don't fall into a
                predictable pattern; see its specific section below.
        - Cambodian Royal Ploughing Ceremony/Preah Neangkol:
                4th Waning Day of Month 6
                (On Month 7 for Athikamat Years).
                This defaults to KHMER_CALENDAR (its sole user).
        - Asalha Puja/Asarnha Bucha:
                15th Waxing Day (Full Moon) of Month 8
                (On Month 8/8 for Athikamat Years).
                KHMER_CALENDAR always fall on Month 8.
        - Buddhist Lent Day/Wan Khao Phansa:
                1st Waning Day of Month 8
                (On Month 8/8 for Athikamat Years).
                KHMER_CALENDAR always fall on Month 8.
        - Pchum Ben/Prachum Bandar:
                15th Waning Day (New Moon) of Month 10.
        - Loy Krathong/Boun That Louang/Bon Om Touk:
                15th Waxing Day (Full Moon) of Month 12.

    Other Buddhist date on Thai Lunar Calendar:
        - Buddha's Cremation Day/Atthami Bucha
                8th Waning Day of  Month 6
                (On Month 7 for Athikamat Years).
                KHMER_CALENDAR always fall on Month 6
        - End of Buddhist Lent Day/Ok Phansa:
                15th Waxing Day (Full Moon) of Month 11

    The following code is based on Ninenik Narkdee's PHP implementation,
    and we're thankful for his work.

    Please avoid touching the Athikawan and Athikamat declaration array
    at all costs unless you can find sources for them somewhere for 2057++

    Sources: (Ninenik.com 's wbm) http://tiny.cc/wa_ninenik_thluncal_php
             https://www.myhora.com/ปฏิทิน/ปฏิทิน-พ.ศ.2560.aspx

    Usage example:

    >>> from holidays.utils import _ThaiLunisolar
    >>> thls = _ThaiLunisolar()
    >>> print(thls.visakha_bucha_date(2010))
    2010-05-28
    """

    # Athikawan (Extra-Day Year) list goes from 1941-2057 C.E.
    # Copied off from 1757-2057 (B.E. 2300-2600) Thai Lunar Calendar
    ATHIKAWAN_YEARS_GREGORIAN = {
        1945,
        1949,
        1952,
        1957,
        1963,
        1970,
        1973,
        1979,
        1987,
        1990,
        1997,
        2000,
        2006,
        2009,
        2016,
        2020,
        2025,
        2032,
        2035,
        2043,
        2046,
        2052,
    }

    # Athikamat (Extra-Month Year) list goes from 1941-2057 C.E.:
    # Copied off from 1757-2057 (B.E. 2300-2600) Thai Lunar Calendar
    # Approx formula as follows: (common_era-78)-0.45222)%2.7118886 < 1
    ATHIKAMAT_YEARS_GREGORIAN = {
        1942,
        1944,
        1947,
        1950,
        1953,
        1956,
        1958,
        1961,
        1964,
        1966,
        1969,
        1972,
        1975,
        1977,
        1980,
        1983,
        1985,
        1988,
        1991,
        1994,
        1996,
        1999,
        2002,
        2004,
        2007,
        2010,
        2012,
        2015,
        2018,
        2021,
        2023,
        2026,
        2029,
        2031,
        2034,
        2037,
        2040,
        2042,
        2045,
        2048,
        2050,
        2053,
        2056,
    }

    # While Buddhist Holy Days have been observed since the 1900s
    #   Due to the calendar changes in 1941 (B.E. 2484) and that
    #   our array only goes up to B.E. 2600; We'll thus only populate
    #   the data for 1941-2057 (B.E. 2484-2600).
    # Sources: หนังสือเวียนกรมการปกครอง กระทรวงมหาดไทย มท 0310.1/ว4 5 ก.พ. 2539
    START_DATE = date(1940, 11, 30)
    START_YEAR = 1941
    END_YEAR = 2057

    def __init__(self, calendar=THAI_CALENDAR) -> None:
        self.__verify_calendar(calendar)
        self.__calendar = calendar

    @staticmethod
    def __is_khmer_calendar(calendar):
        """
        Return True if `calendar` is Khmer calendar.
        Return False otherwise.
        """
        return calendar == KHMER_CALENDAR

    @staticmethod
    def __verify_calendar(calendar):
        """
        Verify calendar type.
        """
        if calendar not in {KHMER_CALENDAR, THAI_CALENDAR}:
            raise ValueError(
                f"Unknown calendar name: {calendar}. Use `KHMER_CALENDAR` or `THAI_CALENDAR`."
            )

    @lru_cache()
    def _get_start_date(self, year: int) -> Optional[date]:
        """
        Calculate the start date of that particular Thai Lunar Calendar Year.
        This usually falls in November or December of the previous Gregorian
        year in question. Should the year be outside of working scope
        (1941-2057: B.E 2484-2600), this will returns None instead.

        :param year:
            The Gregorian year.

        :return:
             The start date of Thai Lunar Calendar for a Gregorian year.
        """
        if year < _ThaiLunisolar.START_YEAR or year > _ThaiLunisolar.END_YEAR:
            return None

        iter_start_date = _ThaiLunisolar.START_DATE
        iter_start_year = _ThaiLunisolar.START_YEAR

        while iter_start_year < year:
            if iter_start_year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN:
                delta_days = 384
            elif iter_start_year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
                delta_days = 355
            else:
                delta_days = 354
            iter_start_date += td(days=delta_days)
            iter_start_year += 1
        return iter_start_date

    def makha_bucha_date(self, year: int, calendar=None) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Makha Bucha.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Magha Puja", "Makha Buxha" and "Meak Bochea".
        This concides with the 15th Waxing Day of Month 3
        in Thai Lunar Calendar, or Month 4 in Athikamat years.

        KHMER_CALENDAR will always use Month 3 regardless of year type.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 4
                     or 29[1] + 30[2] + 29[3] + 15[4] -1 = 102
        - Athikawan: 15th Waxing Day of Month 3
                     or 29[1] + 30[2] + 15[3] -1 = 73
        - Pakatimat: 15th Waxing Day of Month 3
                     or 29[1] + 30[2] + 15[3] -1 = 73

        :param year:
            The Gregorian year.

        :param calendar:
            Calendar type, this defaults to THAI_CALENDAR.

        :return:
            Estimated Gregorian date of Makha Bucha.
        """
        calendar = calendar or self.__calendar
        self.__verify_calendar(calendar)

        start_date = self._get_start_date(year)
        if not start_date:
            return None

        return start_date + td(
            days=+102
            if (
                year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN
                and not self.__is_khmer_calendar(calendar)
            )
            else +73
        )

    def visakha_bucha_date(self, year: int, calendar=None) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Visakha Bucha.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Vesak" and "Buddha Day". This concides with
        the 15th Waxing Day of Month 6 in Thai Lunar Calendar,
        or Month 7 in Athikamat years.

        KHMER_CALENDAR will always use Month 6 regardless of year type.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 7
                     or 177[1-6] + 15[7] -1 = 191
        - Athikawan: 15th Waxing Day of Month 6
                     or 147[1-5] + 15[6] -1 = 161
        - Pakatimat: 15th Waxing Day of Month 6
                     or 147[1-5] + 15[6] -1 = 161

        :param year:
            The Gregorian year.

        :param calendar:
            Calendar type, this defaults to THAI_CALENDAR.

        :return:
            Estimated Gregorian date of Visakha Bucha.
        """
        calendar = calendar or self.__calendar
        self.__verify_calendar(calendar)

        start_date = self._get_start_date(year)
        if not start_date:
            return None

        return start_date + td(
            days=+191
            if (
                year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN
                and not self.__is_khmer_calendar(calendar)
            )
            else +161
        )

    def preah_neangkoal_date(self, year: int) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Preah Neangkoal.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Cambodian Royal Ploughing Ceremony". This always
        concides with the 4th Waning Day of Month 6 in Khmer Lunar Calendar.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 6
                     or 177[1-6] + 19[7] -1 = 165
        - Athikawan: 15th Waxing Day of Month 6
                     or 147[1-5] + 19[6] -1 = 165
        - Pakatimat: 15th Waxing Day of Month 6
                     or 147[1-5] + 19[6] -1 = 165
        Or as in simpler terms: "Visakha Bucha" +4

        :param year:
            The Gregorian year.

        :return:
            Estimated Gregorian date of Preah Neangkoal.
        """
        start_date = self._get_start_date(year)
        if not start_date:
            return None

        return start_date + td(days=+165)

    def atthami_bucha_date(self, year: int, calendar=None) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Atthami Bucha.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Buddha's Cremation Day". This concides with
        the 8th Waning Day of Month 6 in Thai Lunar Calendar,
        or Month 7 in Athikamat years.

        KHMER_CALENDAR will always use Month 6 regardless of year type.

        To calculate, we use use the following time delta:
        - Athikamat: 8th Waning Day of  Month 7
                    or 177[1-6] + 23[7] -1 = 199
        - Athikawan: 8th Waning Day of  Month 6
                     or 147[1-5] + 23[6] -1 = 169
        - Pakatimat: 8th Waning Day of  Month 6
                    or 147[1-5] + 23[6] -1 = 169
        - Or as in simpler terms: "Visakha Bucha" +8

        :param year:
            The Gregorian year.

        :param calendar:
            Calendar type, this defaults to THAI_CALENDAR.

        :return:
            Estimated Gregorian date of Atthami Bucha.
        """
        calendar = calendar or self.__calendar
        self.__verify_calendar(calendar)

        start_date = self._get_start_date(year)
        if not start_date:
            return None

        return start_date + td(
            days=+199
            if (
                year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN
                and not self.__is_khmer_calendar(calendar)
            )
            else +169
        )

    def asarnha_bucha_date(self, year: int, calendar=None) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Asarnha Bucha.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Asalha Puja". This concides with
        the 15th Waxing Day of Month 8 in Thai Lunar Calendar,
        or Month 8.8 in Athikamat years.

        KHMER_CALENDAR will always use Month 8 regardless of year type.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 8/8
                     or 177[1-6] + 29[7] + 30[8] + 15[8.8] -1 = 250
        - Athikawan: 15th Waxing Day of Month 8
                     or 177[1-6] + 30[7] + 15[8] -1 = 221
        - Pakatimat: 15th Waxing Day of Month 8
                     or 177[1-6] + 29[7] + 15[8] -1 = 220

        :param year:
            The Gregorian year.

        :param calendar:
            Calendar type, this defaults to THAI_CALENDAR.

        :return:
            Estimated Gregorian date of Asarnha Bucha.
        """
        calendar = calendar or self.__calendar
        self.__verify_calendar(calendar)

        start_date = self._get_start_date(year)
        if not start_date:
            return None

        if year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN and not self.__is_khmer_calendar(
            calendar
        ):
            delta_days = 250
        elif year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
            delta_days = 221
        else:
            delta_days = 220
        return start_date + td(days=delta_days)

    def khao_phansa_date(self, year: int, calendar=None) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Khao Phansa.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "(Start of) Buddhist Lent" and "Start of Vassa".
        This concides with the 1st Waning Day of Month 8
        in Thai Lunar Calendar, or Month 8.8 in Athikamat years.

        KHMER_CALENDAR will always use Month 8 regardless of year type.

        To calculate, we use use the following time delta:
        - Athikamat: 1st Waning Day of Month 8.8
                     or 177[1-6] + 29[7] + 30[8] + 16[8.8] -1 = 251
        - Athikawan: 1st Waning Day of Month 8 ]
                     or 177[1-6] + 30[7] + 16[8] -1 = 222
        - Pakatimat: 1st Waning Day of Month 8
                     or 177[1-6] + 29[7] + 16[8] -1 = 221
        - Or as in simpler terms: "Asarnha Bucha" +1

        :param year:
            The Gregorian year.

        :param calendar:
            Calendar type, this defaults to THAI_CALENDAR.

        :return:
            Estimated Gregorian date of Khao Phansa.
        """
        calendar = calendar or self.__calendar
        self.__verify_calendar(calendar)

        start_date = self._get_start_date(year)
        if not start_date:
            return None

        if year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN and not self.__is_khmer_calendar(
            calendar
        ):
            delta_days = 251
        elif year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
            delta_days = 222
        else:
            delta_days = 221
        return start_date + td(days=delta_days)

    def pchum_ben_date(self, year: int) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Pchum Ben.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Prachum Bandar".
        This concides with the 15th Waning Day of Month 10 in
        Thai Lunar Calendar.

         To calculate, we use use the following time delta:
        - Athikamat: 15th Waning Day of Month 10
                     or 265[1-9] + 30[8.8] + 30[10] -1 = 324
        - Athikawan: 15th Waning Day of Month 10
                     or 265[1-9] + 1[7] + 30[10] -1 = 295
        - Pakatimat: 15th Waning Day of Month 10
                     or 265[1-9] + 30[10] -1 = 294

        :param year:
            The Gregorian year.

        :return:
            Estimated Gregorian date of Pchum Ben.
        """
        start_date = self._get_start_date(year)
        if not start_date:
            return None

        if year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN:
            delta_days = 324
        elif year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
            delta_days = 295
        else:
            delta_days = 294
        return start_date + td(days=delta_days)

    def ok_phansa_date(self, year: int) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Ok Phansa.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "End of Buddhist Lent" and "End of Vassa".
        This concides with the 15th Waxing Day of Month 11
        in Thai Lunar Calendar.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 11
                     or 295[1-10] + 30[8.8] + 15[11] -1 = 339
        - Athikawan: 15th Waxing Day of Month 11
                     or 295[1-10] + 1[7] + 15[11] -1 = 310
        - Pakatimat: 15th Waxing Day of Month 11
                     or 295[1-10] + 15[11] -1 = 309

        :param year:
            The Gregorian year.

        :return:
            Estimated Gregorian date of Ok Phansa.
        """
        start_date = self._get_start_date(year)
        if not start_date:
            return None

        if year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN:
            delta_days = 339
        elif year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
            delta_days = 310
        else:
            delta_days = 309
        return start_date + td(days=delta_days)

    def loy_krathong_date(self, year: int) -> Optional[date]:
        """
        Calculate the estimated Gregorian date of Loy Krathong.
        If the Gregorian year input is invalid, this will outputs None instead.

        Also known as "Boun That Louang" and "Bon Om Touk".
        This concides with the 15th Waxing Day of Month 12
        in Thai Lunar Calendar.

        To calculate, we use use the following time delta:
        - Athikamat: 15th Waxing Day of Month 12
                     or 324[1-11] + 30[8.8] + 15[11] -1 = 368
        - Athikawan: 15th Waxing Day of Month 12
                     or 324[1-11] + 1[7] + 15[11] -1 = 339
        - Pakatimat: 15th Waxing Day of Month 12
                     or 324[1-11] + 15[11] -1 = 338

        :param year:
            The Gregorian year.

        :return:
            Estimated Gregorian date of Loy Krathong.
        """
        start_date = self._get_start_date(year)
        if not start_date:
            return None

        if year in _ThaiLunisolar.ATHIKAMAT_YEARS_GREGORIAN:
            delta_days = 368
        elif year in _ThaiLunisolar.ATHIKAWAN_YEARS_GREGORIAN:
            delta_days = 339
        else:
            delta_days = 338
        return start_date + td(days=delta_days)
