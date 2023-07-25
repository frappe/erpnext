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

from holidays.calendars.gregorian import (
    JAN,
    FEB,
    MAR,
    APR,
    JUN,
    JUL,
    SEP,
    OCT,
    NOV,
    DEC,
    MON,
    TUE,
    WED,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class NewZealand(HolidayBase, ChristianHolidays, InternationalHolidays):
    country = "NZ"
    special_holidays = {
        2022: (SEP, 26, "Queen Elizabeth II Memorial Day"),
    }
    subdivisions = (
        # https://en.wikipedia.org/wiki/ISO_3166-2:NZ
        "AUK",  # Auckland / Tāmaki-makaurau
        "BOP",  # Bay of Plenty / Toi Moana
        "CAN",  # Canterbury / Waitaha
        "CIT",  # Chatham Islands Territory / Wharekauri
        "GIS",  # Gisborne / Te Tairāwhiti
        "HKB",  # Hawke's Bay / Te Matau a Māui
        "MBH",  # Marlborough
        "MWT",  # Manawatū Whanganui
        "NSN",  # Nelson / Whakatū
        "NTL",  # Northland / Te Tai tokerau
        "OTA",  # Otago / Ō Tākou
        "STL",  # Southland / Te Taiao Tonga
        "TAS",  # Tasman / Te tai o Aorere
        "TKI",  # Taranaki
        "WGN",  # Greater Wellington / Te Pane Matua Taiao
        "WKO",  # Waikato
        "WTC",  # West Coast / Te Tai o Poutini
    )

    _deprecated_subdivisions = (
        "Auckland",
        "Canterbury",
        "Chatham Islands",
        "Hawke's Bay",
        "Marlborough",
        "Nelson",
        "New Plymouth",
        "Northland",
        "Otago",
        "South Canterbury",
        "STC",
        "Southland",
        "Taranaki",
        "Waitangi",
        "Wellington",
        "West Coast",
        "Westland",  # Correct name is West Coast
        "WTL",  # Correct code is WTC
    )

    def _get_nearest_monday(self, *args) -> date:
        dt = date(self._year, *args)
        return self._get_nth_weekday_from(
            1 if self._is_friday(dt) or self._is_weekend(dt) else -1, MON, dt
        )

    def _add_observed(self, dt: date, days: int = +1) -> None:
        if self.observed and self._is_weekend(dt):
            self._add_holiday(
                "%s (Observed)" % self[dt], dt + td(days=+2 if self._is_saturday(dt) else days)
            )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # Bank Holidays Act 1873
        # The Employment of Females Act 1873
        # Factories Act 1894
        # Industrial Conciliation and Arbitration Act 1894
        # Labour Day Act 1899
        # Anzac Day Act 1920, 1949, 1956
        # New Zealand Day Act 1973
        # Waitangi Day Act 1960, 1976
        # Sovereign's Birthday Observance Act 1937, 1952
        # Holidays Act 1981, 2003

        if year <= 1893:
            return None

        super()._populate(year)

        # New Year's Day
        self._add_observed(self._add_new_years_day("New Year's Day"), days=+2)
        self._add_observed(self._add_new_years_day_two("Day after New Year's Day"), days=+2)

        # Waitangi Day
        if year >= 1974:
            name = "Waitangi Day" if year >= 1977 else "New Zealand Day"
            feb_6 = self._add_holiday(name, FEB, 6)
            if year >= 2014:
                self._add_observed(feb_6)

        # Anzac Day
        if year >= 1921:
            apr_25 = self._add_holiday("Anzac Day", APR, 25)
            if year >= 2014:
                self._add_observed(apr_25)

        # Easter
        self._add_good_friday("Good Friday")
        self._add_easter_monday("Easter Monday")

        # Sovereign's Birthday
        if year >= 1902:
            name = "Queen's Birthday" if 1952 <= year <= 2022 else "King's Birthday"
            if year == 1952:
                dt = date(year, JUN, 2)  # Elizabeth II
            elif year >= 1938:
                dt = self._get_nth_weekday_of_month(1, MON, JUN)  # EII & GVI
            elif year == 1937:
                dt = date(year, JUN, 9)  # George VI
            elif year == 1936:
                dt = date(year, JUN, 23)  # Edward VIII
            elif year >= 1912:
                dt = date(year, JUN, 3)  # George V
            else:
                # http://paperspast.natlib.govt.nz/cgi-bin/paperspast?a=d&d=NZH19091110.2.67
                dt = date(year, NOV, 9)  # Edward VII
            self._add_holiday(name, dt)

        # Matariki
        dates_obs = {
            2022: (JUN, 24),
            2023: (JUL, 14),
            2024: (JUN, 28),
            2025: (JUN, 20),
            2026: (JUL, 10),
            2027: (JUN, 25),
            2028: (JUL, 14),
            2029: (JUL, 6),
            2030: (JUN, 21),
            2031: (JUL, 11),
            2032: (JUL, 2),
            2033: (JUN, 24),
            2034: (JUL, 7),
            2035: (JUN, 29),
            2036: (JUL, 18),
            2037: (JUL, 10),
            2038: (JUN, 25),
            2039: (JUL, 15),
            2040: (JUL, 6),
            2041: (JUL, 19),
            2042: (JUL, 11),
            2043: (JUL, 3),
            2044: (JUN, 24),
            2045: (JUL, 7),
            2046: (JUN, 29),
            2047: (JUL, 19),
            2048: (JUL, 3),
            2049: (JUN, 25),
            2050: (JUL, 15),
            2051: (JUN, 30),
            2052: (JUN, 21),
        }
        if year in dates_obs:
            self._add_holiday("Matariki", *dates_obs[year])

        # Labour Day
        if year >= 1900:
            dt = (
                self._get_nth_weekday_of_month(4, MON, OCT)
                if year >= 1910
                else self._get_nth_weekday_of_month(2, WED, OCT)
            )
            self._add_holiday("Labour Day", dt)

        # Christmas Day
        self._add_observed(self._add_christmas_day("Christmas Day"), days=+2)

        # Boxing Day
        self._add_observed(self._add_christmas_day_two("Boxing Day"), days=+2)

        if self.subdiv == "Auckland":
            self._add_subdiv_auk_holidays()
        elif self.subdiv == "Canterbury":
            self._add_subdiv_can_holidays()
        elif self.subdiv == "Chatham Islands":
            self._add_subdiv_cit_holidays()
        elif self.subdiv == "Hawke's Bay":
            self._add_subdiv_hkb_holidays()
        elif self.subdiv == "Marlborough":
            self._add_subdiv_mbh_holidays()
        elif self.subdiv == "Nelson":
            self._add_subdiv_nsn_holidays()
        elif self.subdiv == "Northland":
            self._add_subdiv_ntl_holidays()
        elif self.subdiv == "Otago":
            self._add_subdiv_ota_holidays()
        elif self.subdiv in {"New Plymouth", "Taranaki"}:
            self._add_subdiv_tki_holidays()
        elif self.subdiv == "South Canterbury":
            self._add_subdiv_stc_holidays()
        elif self.subdiv == "Southland":
            self._add_subdiv_stl_holidays()
        elif self.subdiv == "Wellington":
            self._add_subdiv_wgn_holidays()
        elif self.subdiv in {"West Coast", "WTL", "Westland"}:
            self._add_subdiv_wtc_holidays()

    def _add_subdiv_auk_holidays(self):
        self._add_holiday("Auckland Anniversary Day", self._get_nearest_monday(JAN, 29))

    def _add_subdiv_can_holidays(self):
        self._add_holiday(
            "Canterbury Anniversary Day",
            self._get_nth_weekday_of_month(1, TUE, NOV) + td(days=+10),
        )

    def _add_subdiv_cit_holidays(self):
        self._add_holiday("Chatham Islands Anniversary Day", self._get_nearest_monday(NOV, 30))

    def _add_subdiv_hkb_holidays(self):
        self._add_holiday(
            "Hawke's Bay Anniversary Day",
            self._get_nth_weekday_of_month(4, MON, OCT) + td(days=-3),
        )

    def _add_subdiv_mbh_holidays(self):
        self._add_holiday(
            "Marlborough Anniversary Day",
            self._get_nth_weekday_of_month(4, MON, OCT) + td(days=+7),
        )

    def _add_subdiv_nsn_holidays(self):
        self._add_holiday("Nelson Anniversary Day", self._get_nearest_monday(FEB, 1))

    def _add_subdiv_ntl_holidays(self):
        if 1964 <= self._year <= 1973:
            name = "Waitangi Day"
            dt = (FEB, 6)
        else:
            name = "Auckland Anniversary Day"
            dt = (JAN, 29)
        self._add_holiday(name, self._get_nearest_monday(*dt))

    def _add_subdiv_ota_holidays(self):
        # there is no easily determined single day of local observance?!?!
        dt = self._get_nearest_monday(MAR, 23)
        if dt == self._easter_sunday + td(days=+1):  # Avoid Easter Monday
            dt += td(days=+1)
        self._add_holiday("Otago Anniversary Day", dt)

    def _add_subdiv_stc_holidays(self):
        self._add_holiday(
            "South Canterbury Anniversary Day", self._get_nth_weekday_of_month(4, MON, SEP)
        )

    def _add_subdiv_stl_holidays(self):
        dt = (
            self._easter_sunday + td(days=+2)
            if self._year >= 2012
            else self._get_nearest_monday(JAN, 17)
        )
        self._add_holiday("Southland Anniversary Day", dt)

    def _add_subdiv_tki_holidays(self):
        self._add_holiday("Taranaki Anniversary Day", self._get_nth_weekday_of_month(2, MON, MAR))

    def _add_subdiv_wgn_holidays(self):
        self._add_holiday("Wellington Anniversary Day", self._get_nearest_monday(JAN, 22))

    def _add_subdiv_wtc_holidays(self):
        dt = (
            date(self._year, DEC, 5)
            if self._year == 2005  # special case?!?!
            else self._get_nearest_monday(DEC, 1)
        )
        self._add_holiday("West Coast Anniversary Day", dt)


class NZ(NewZealand):
    pass


class NZL(NewZealand):
    pass
