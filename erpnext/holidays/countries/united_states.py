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
from typing import Tuple, Union

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
    TUE,
    THU,
    FRI,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class UnitedStates(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_the_United_States

    For Northern Mariana Islands (subdivision MP):
    https://governor.gov.mp/archived-news/executive-actions-archive/memorandum-2022-legal-holidays/
    https://webcache.googleusercontent.com/search?q=cache:C17_7FBgPtQJ:https://governor.gov.mp/archived-news/executive-actions-archive/memorandum-2022-legal-holidays/&hl=en&gl=sg&strip=1&vwsrc=0
    """

    country = "US"
    subdivisions: Union[Tuple[()], Tuple[str, ...]] = (
        "AK",
        "AL",
        "AR",
        "AS",
        "AZ",
        "CA",
        "CO",
        "CT",
        "DC",
        "DE",
        "FL",
        "FM",
        "GA",
        "GU",
        "HI",
        "IA",
        "ID",
        "IL",
        "IN",
        "KS",
        "KY",
        "LA",
        "MA",
        "MD",
        "ME",
        "MH",
        "MI",
        "MN",
        "MO",
        "MP",
        "MS",
        "MT",
        "NC",
        "ND",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NV",
        "NY",
        "OH",
        "OK",
        "OR",
        "PA",
        "PR",
        "PW",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UM",
        "UT",
        "VA",
        "VI",
        "VT",
        "WA",
        "WI",
        "WV",
        "WY",
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date, before: bool = True, after: bool = True) -> None:
        if not self.observed:
            return None
        if self._is_saturday(dt) and before:
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=-1))
        elif self._is_sunday(dt) and after:
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day
        if year >= 1871:
            name = "New Year's Day"
            self._add_observed(self._add_new_years_day(name), before=False)
            # The following year's observed New Year's Day can be in this year
            # when it falls on a Friday (Jan 1st is a Saturday).
            if self.observed and self._is_friday(DEC, 31):
                self._add_holiday("%s (Observed)" % name, DEC, 31)

        # Memorial Day
        if year >= 1888:
            self._add_holiday(
                "Memorial Day",
                self._get_nth_weekday_of_month(-1, MON, MAY)
                if year >= 1971
                else date(year, MAY, 30),
            )

        # Juneteenth Day
        if year >= 2021:
            self._add_observed(self._add_holiday("Juneteenth National Independence Day", JUN, 19))

        # Independence Day
        if year >= 1871:
            self._add_observed(self._add_holiday("Independence Day", JUL, 4))

        # Labor Day
        if year >= 1894:
            self._add_holiday("Labor Day", self._get_nth_weekday_of_month(1, MON, SEP))

        # Veterans Day
        if year >= 1938:
            name = "Veterans Day" if year >= 1954 else "Armistice Day"
            if 1971 <= year <= 1977:
                self._add_holiday(name, self._get_nth_weekday_of_month(4, MON, OCT))
            else:
                self._add_observed(self._add_remembrance_day(name))

        # Thanksgiving
        if year >= 1871:
            self._add_holiday("Thanksgiving", self._get_nth_weekday_of_month(4, THU, NOV))

        # Christmas Day
        if year >= 1871:
            self._add_observed(self._add_christmas_day("Christmas Day"))

    def _add_christmas_eve_holiday(self):
        # Christmas Eve
        name = "Christmas Eve"
        dt = self._add_christmas_eve(name)
        if self.observed:
            # If on Friday, observed on Thursday
            if self._is_friday(dt):
                self._add_holiday("%s (Observed)" % name, dt + td(days=-1))
            # If on Saturday or Sunday, observed on Friday
            elif self._is_weekend(dt):
                self._add_holiday("%s (Observed)" % name, self._get_nth_weekday_from(-1, FRI, dt))

    def _add_subdiv_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986 and self.subdiv not in {"AL", "AR", "AZ", "GA", "ID", "MS", "NH"}:
            self._add_holiday(
                "Martin Luther King Jr. Day", self._get_nth_weekday_of_month(3, MON, JAN)
            )

        # Washington's Birthday
        if self._year >= 1879 and self.subdiv not in {
            "AL",
            "AR",
            "DE",
            "FL",
            "GA",
            "NM",
            "PR",
            "VI",
        }:
            self._add_holiday(
                "Washington's Birthday",
                self._get_nth_weekday_of_month(3, MON, FEB)
                if self._year >= 1971
                else date(self._year, FEB, 22),
            )

        # Columbus Day
        if self._year >= 1937 and self.subdiv not in {
            "AK",
            "AR",
            "DE",
            "FL",
            "HI",
            "NV",
            "SD",
            "VI",
        }:
            name = "Columbus Day"
            if self._year >= 1970:
                self._add_holiday(name, self._get_nth_weekday_of_month(2, MON, OCT))
            else:
                self._add_columbus_day(name)

        super()._add_subdiv_holidays()

    def _add_subdiv_ak_holidays(self):
        # Seward's Day
        if self._year >= 1918:
            self._add_holiday(
                "Seward's Day",
                self._get_nth_weekday_of_month(-1, MON, MAR)
                if self._year >= 1955
                else date(self._year, MAR, 30),
            )

        # Alaska Day
        if self._year >= 1867:
            self._add_observed(self._add_holiday("Alaska Day", OCT, 18))

    def _add_subdiv_al_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Martin Luther King, Jr & Robert E. Lee's Birthday",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

        # Washington's Birthday
        self._add_holiday(
            "George Washington & Thomas Jefferson's Birthday",
            self._get_nth_weekday_of_month(3, MON, FEB)
            if self._year >= 1971
            else date(self._year, FEB, 22),
        )

        # Confederate Memorial Day
        if self._year >= 1866:
            self._add_holiday(
                "Confederate Memorial Day", self._get_nth_weekday_of_month(4, MON, APR)
            )

        # Jefferson Davis Birthday
        if self._year >= 1890:
            self._add_holiday(
                "Jefferson Davis Birthday", self._get_nth_weekday_of_month(1, MON, JUN)
            )

    def _add_subdiv_ar_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Martin Luther King Jr. Day"
                if self._year >= 2018
                else "Dr. Martin Luther King Jr. " "and Robert E. Lee's Birthdays",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

        # Washington's Birthday
        self._add_holiday(
            "George Washington's Birthday and Daisy Gatson Bates Day",
            self._get_nth_weekday_of_month(3, MON, FEB)
            if self._year >= 1971
            else date(self._year, FEB, 22),
        )

    def _add_subdiv_as_holidays(self):
        # Christmas Eve
        self._add_christmas_eve_holiday()

    def _add_subdiv_az_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Dr. Martin Luther King Jr. / Civil Rights Day",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

    def _add_subdiv_ca_holidays(self):
        # Lincoln's Birthday
        if 1971 <= self._year <= 2009:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

        # Susan B. Anthony Day
        if self._year >= 2014:
            self._add_holiday("Susan B. Anthony Day", FEB, 15)

        # Cesar Chavez Day
        if self._year >= 1995:
            self._add_observed(self._add_holiday("Cesar Chavez Day", MAR, 31), before=False)

        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_co_holidays(self):
        pass

    def _add_subdiv_ct_holidays(self):
        # Lincoln's Birthday
        if self._year >= 1971:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

        # Good Friday
        self._add_good_friday("Good Friday")

    def _add_subdiv_dc_holidays(self):
        # Inauguration Day
        if self._year >= 1789 and (self._year - 1789) % 4 == 0:
            dt = (JAN, 20) if self._year >= 1937 else (MAR, 4)
            self._add_observed(self._add_holiday("Inauguration Day", *dt), before=False)

        # Emancipation Day
        if self._year >= 2005:
            self._add_observed(self._add_holiday("Emancipation Day", APR, 16))

    def _add_subdiv_de_holidays(self):
        # Good Friday
        self._add_good_friday("Good Friday")

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_fl_holidays(self):
        # Susan B. Anthony Day
        if self._year >= 2011:
            self._add_holiday("Susan B. Anthony Day", FEB, 15)

        # Friday After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Friday After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_fm_holidays(self):
        pass

    def _add_subdiv_ga_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Martin Luther King Jr. Day" if self._year >= 2012 else "Robert E. Lee's Birthday",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

        # Confederate Memorial Day
        if self._year >= 1866:
            self._add_holiday(
                "State Holiday" if self._year >= 2016 else "Confederate Memorial Day",
                date(self._year, APR, 10)
                if self._year == 2020
                else self._get_nth_weekday_of_month(4, MON, APR),
            )

        # Robert E. Lee's Birthday
        if self._year >= 1986:
            self._add_holiday(
                "State Holiday" if self._year >= 2016 else "Robert E. Lee's Birthday",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

        # Washington's Birthday
        dt = (DEC, 24)
        if self._is_wednesday(*dt):
            dt = (DEC, 26)
        self._add_holiday("Washington's Birthday", *dt)

    def _add_subdiv_gu_holidays(self):
        # Guam Discovery Day
        if self._year >= 1970:
            self._add_holiday("Guam Discovery Day", self._get_nth_weekday_of_month(1, MON, MAR))

        # Good Friday
        self._add_good_friday("Good Friday")

        # Liberation Day (Guam)
        if self._year >= 1945:
            self._add_holiday("Liberation Day (Guam)", JUL, 21)

        # All Souls' Day
        self._add_all_souls_day("All Souls' Day")

        # Lady of Camarin Day
        self._add_immaculate_conception_day("Lady of Camarin Day")

    def _add_subdiv_hi_holidays(self):
        # Prince Jonah Kuhio Kalanianaole Day
        if self._year >= 1949:
            self._add_observed(self._add_holiday("Prince Jonah Kuhio Kalanianaole Day", MAR, 26))

        # Kamehameha Day
        if self._year >= 1872:
            jun_11 = self._add_holiday("Kamehameha Day", JUN, 11)
            if self._year >= 2011:
                self._add_observed(jun_11)

        # Statehood Day
        if self._year >= 1959:
            self._add_holiday("Statehood Day", self._get_nth_weekday_of_month(3, FRI, AUG))

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_ia_holidays(self):
        # Lincoln's Birthday
        if self._year >= 1971:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

    def _add_subdiv_id_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Martin Luther King Jr. / Idaho Human Rights Day"
                if self._year >= 2006
                else "Martin Luther King Jr. Day",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

    def _add_subdiv_il_holidays(self):
        # Lincoln's Birthday
        if self._year >= 1971:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

        # Casimir Pulaski Day
        if self._year >= 1978:
            self._add_holiday("Casimir Pulaski Day", self._get_nth_weekday_of_month(1, MON, MAR))

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_in_holidays(self):
        # Good Friday
        self._add_good_friday("Good Friday")

        # Primary Election Day
        if self._year >= 2015 or (self._year >= 2006 and self._year % 2 == 0):
            self._add_holiday(
                "Primary Election Day",
                self._get_nth_weekday_of_month(1, MON, MAY) + td(days=+1),
            )

        # Election Day
        if self._year >= 2015 or (self._year >= 2008 and self._year % 2 == 0):
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

        # Lincoln's Birthday
        if self._year >= 2010:
            self._add_holiday(
                "Lincoln's Birthday",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_ks_holidays(self):
        # Christmas Eve
        if self._year >= 2013:
            self._add_christmas_eve_holiday()

    def _add_subdiv_ky_holidays(self):
        # Good Friday
        self._add_good_friday("Good Friday")

        # New Year's Eve
        if self._year >= 2013:
            self._add_observed(self._add_new_years_eve("New Year's Eve"), after=False)

    def _add_subdiv_la_holidays(self):
        # Inauguration Day
        if self._year >= 1789 and (self._year - 1789) % 4 == 0:
            dt = (JAN, 20) if self._year >= 1937 else (MAR, 4)
            self._add_observed(self._add_holiday("Inauguration Day", *dt), before=False)

        # Mardi Gras
        if self._year >= 1857:
            self._add_carnival_tuesday("Mardi Gras")

        # Good Friday
        self._add_good_friday("Good Friday")

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_ma_holidays(self):
        # Evacuation Day
        if self._year >= 1901:
            mar_17 = self._add_holiday("Evacuation Day", MAR, 17)
            if self.observed and self._is_weekend(mar_17):
                self._add_holiday(
                    "%s (Observed)" % self[mar_17], self._get_nth_weekday_from(1, MON, mar_17)
                )

        # Patriots' Day
        if self._year >= 1894:
            self._add_holiday(
                "Patriots' Day",
                self._get_nth_weekday_of_month(3, MON, APR)
                if self._year >= 1969
                else date(self._year, APR, 19),
            )

    def _add_subdiv_md_holidays(self):
        # Inauguration Day
        if self._year >= 1789 and (self._year - 1789) % 4 == 0:
            dt = (JAN, 20) if self._year >= 1937 else (MAR, 4)
            self._add_observed(self._add_holiday("Inauguration Day", *dt), before=False)

        # American Indian Heritage Day
        if self._year >= 2008:
            self._add_holiday(
                "American Indian Heritage Day",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_me_holidays(self):
        # Patriots' Day
        if self._year >= 1894:
            self._add_holiday(
                "Patriots' Day",
                self._get_nth_weekday_of_month(3, MON, APR)
                if self._year >= 1969
                else date(self._year, APR, 19),
            )

    def _add_subdiv_mh_holidays(self):
        pass

    def _add_subdiv_mi_holidays(self):
        if self._year >= 2013:
            # Christmas Eve
            self._add_christmas_eve_holiday()

            # New Year's Eve
            self._add_observed(self._add_new_years_eve("New Year's Eve"), after=False)

    def _add_subdiv_mn_holidays(self):
        pass

    def _add_subdiv_mo_holidays(self):
        # Truman Day
        if self._year >= 1949:
            self._add_observed(self._add_holiday("Truman Day", MAY, 8))

    def _add_subdiv_mp_holidays(self):
        # Commonwealth Covenant Day in Northern Mariana Islands
        self._add_observed(self._add_holiday("Commonwealth Covenant Day", MAR, 24))

        # Good Friday
        self._add_good_friday("Good Friday")

        # Commonwealth Cultural Day in Northern Mariana Islands
        self._add_holiday("Commonwealth Cultural Day", self._get_nth_weekday_of_month(2, MON, OCT))

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

        # Citizenship Day in Northern Mariana Islands
        self._add_observed(self._add_holiday("Citizenship Day", NOV, 4))

        # Constitution Day in Northern Mariana Islands
        self._add_observed(self._add_holiday("Constitution Day", DEC, 8))

    def _add_subdiv_ms_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Dr. Martin Luther King Jr. and Robert E. Lee's Birthdays",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

        # Confederate Memorial Day
        if self._year >= 1866:
            self._add_holiday(
                "Confederate Memorial Day", self._get_nth_weekday_of_month(4, MON, APR)
            )

    def _add_subdiv_mt_holidays(self):
        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_nc_holidays(self):
        # Good Friday
        self._add_good_friday("Good Friday")

        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

        # Christmas Eve
        if self._year >= 2013:
            self._add_christmas_eve_holiday()

        # Day After Christmas
        if self._year >= 2013:
            name = "Day After Christmas"
            dt = self._add_christmas_day_two(name)
            if self.observed:
                # If on Saturday or Sunday, observed on Monday
                if self._is_weekend(dt):
                    self._add_holiday(
                        "%s (Observed)" % name, self._get_nth_weekday_from(1, MON, dt)
                    )
                # If on Monday, observed on Tuesday
                elif self._is_monday(dt):
                    self._add_holiday("%s (Observed)" % name, dt + td(days=+1))

    def _add_subdiv_nd_holidays(self):
        pass

    def _add_subdiv_ne_holidays(self):
        # Arbor Day
        if self._year >= 1875:
            self._add_holiday(
                "Arbor Day",
                self._get_nth_weekday_of_month(-1, FRI, APR)
                if self._year >= 1989
                else date(self._year, APR, 22),
            )

    def _add_subdiv_nh_holidays(self):
        # Martin Luther King Jr. Day
        if self._year >= 1986:
            self._add_holiday(
                "Dr. Martin Luther King Jr. / Civil Rights Day",
                self._get_nth_weekday_of_month(3, MON, JAN),
            )

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_nj_holidays(self):
        # Lincoln's Birthday
        if self._year >= 1971:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

        # Good Friday
        self._add_good_friday("Good Friday")

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_nm_holidays(self):
        # Presidents' Day
        self._add_holiday(
            "Presidents' Day",
            self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
        )

    def _add_subdiv_nv_holidays(self):
        # Nevada Day
        if self._year >= 1933:
            self._add_observed(
                self._add_holiday(
                    "Nevada Day",
                    self._get_nth_weekday_of_month(-1, FRI, OCT)
                    if self._year >= 2000
                    else date(self._year, OCT, 31),
                )
            )

        # Family Day
        self._add_holiday("Family Day", self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1))

    def _add_subdiv_ny_holidays(self):
        # Lincoln's Birthday
        if self._year >= 1971:
            self._add_observed(self._add_holiday("Lincoln's Birthday", FEB, 12))

        # Susan B. Anthony Day
        if self._year >= 2004:
            self._add_holiday("Susan B. Anthony Day", FEB, 15)

        # Election Day
        if self._year >= 2015 or (self._year >= 2008 and self._year % 2 == 0):
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

    def _add_subdiv_oh_holidays(self):
        pass

    def _add_subdiv_ok_holidays(self):
        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_or_holidays(self):
        pass

    def _add_subdiv_pa_holidays(self):
        # Day After Thanksgiving
        self._add_holiday(
            "Day After Thanksgiving",
            self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
        )

    def _add_subdiv_pr_holidays(self):
        # Epiphany
        self._add_epiphany_day("Epiphany")

        # Washington's Birthday
        self._add_holiday("Presidents' Day", self._get_nth_weekday_of_month(3, MON, FEB))

        # Emancipation Day
        self._add_observed(self._add_holiday("Emancipation Day", MAR, 22), before=False)

        # Good Friday
        self._add_good_friday("Good Friday")

        # Constitution Day
        self._add_observed(self._add_holiday("Constitution Day", JUL, 25), before=False)

        # Discovery Day
        self._add_observed(self._add_holiday("Discovery Day", NOV, 19), before=False)

    def _add_subdiv_pw_holidays(self):
        pass

    def _add_subdiv_ri_holidays(self):
        # Victory Day
        if self._year >= 1948:
            self._add_holiday("Victory Day", self._get_nth_weekday_of_month(2, MON, AUG))

    def _add_subdiv_sc_holidays(self):
        # Confederate Memorial Day
        if self._year >= 1866:
            self._add_holiday(
                "Confederate Memorial Day", self._get_nth_weekday_of_month(4, MON, APR)
            )

    def _add_subdiv_sd_holidays(self):
        # Columbus Day
        if self._year >= 1937:
            name = "Native American Day"
            if self._year >= 1970:
                self._add_holiday(name, self._get_nth_weekday_of_month(2, MON, OCT))
            else:
                self._add_columbus_day(name)

    def _add_subdiv_tn_holidays(self):
        # Good Friday
        self._add_good_friday("Good Friday")

    def _add_subdiv_tx_holidays(self):
        # Confederate Memorial Day
        if self._year >= 1931:
            self._add_holiday("Confederate Memorial Day", JAN, 19)

        # Texas Independence Day
        if self._year >= 1874:
            self._add_holiday("Texas Independence Day", MAR, 2)

        # Cesar Chavez Day
        if self._year >= 2000:
            self._add_holiday("Cesar Chavez Day", MAR, 31)

        # Good Friday
        self._add_good_friday("Good Friday")

        # San Jacinto Day
        if self._year >= 1875:
            self._add_holiday("San Jacinto Day", APR, 21)

        # Emancipation Day In Texas
        if self._year >= 1980:
            self._add_holiday("Emancipation Day In Texas", JUN, 19)

        # Lyndon Baines Johnson Day
        if self._year >= 1973:
            self._add_holiday("Lyndon Baines Johnson Day", AUG, 27)

        # Friday After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Friday After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

        # Christmas Eve
        if self._year >= 1981:
            self._add_christmas_eve_holiday()

        # Day After Christmas
        if self._year >= 1981:
            self._add_christmas_day_two("Day After Christmas")

    def _add_subdiv_um_holidays(self):
        pass

    def _add_subdiv_ut_holidays(self):
        # Pioneer Day
        if self._year >= 1849:
            self._add_observed(self._add_holiday("Pioneer Day", JUL, 24))

    def _add_subdiv_va_holidays(self):
        # Lee Jackson Day
        if 1889 <= self._year <= 2020:
            if self._year >= 2000:
                dt = self._get_nth_weekday_of_month(3, MON, JAN) + td(days=-3)
            elif self._year >= 1983:
                dt = self._get_nth_weekday_of_month(3, MON, JAN)
            else:
                dt = date(self._year, JAN, 19)
            self._add_holiday("Lee Jackson Day", dt)

        # Inauguration Day
        if self._year >= 1789 and (self._year - 1789) % 4 == 0:
            dt = (JAN, 20) if self._year >= 1937 else (MAR, 4)
            self._add_observed(self._add_holiday("Inauguration Day", *dt), before=False)

    def _add_subdiv_vi_holidays(self):
        # Three Kings Day
        self._add_epiphany_day("Three Kings Day")

        # Washington's Birthday
        self._add_holiday(
            "Presidents' Day",
            self._get_nth_weekday_of_month(3, MON, FEB)
            if self._year >= 1971
            else date(self._year, FEB, 22),
        )

        # Transfer Day
        self._add_holiday("Transfer Day", MAR, 31)

        # Holy Thursday
        self._add_holy_thursday("Holy Thursday")

        # Good Friday
        self._add_good_friday("Good Friday")

        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # Emancipation Day in US Virgin Islands
        self._add_holiday("Emancipation Day", JUL, 3)

        # Columbus Day
        if self._year >= 1937:
            name = "Columbus Day and Puerto Rico Friendship Day"
            if self._year >= 1970:
                self._add_holiday(name, self._get_nth_weekday_of_month(2, MON, OCT))
            else:
                self._add_columbus_day(name)

        # Liberty Day
        self._add_holiday("Liberty Day", NOV, 1)

        # Christmas Second Day
        self._add_christmas_day_two("Christmas Second Day")

    def _add_subdiv_vt_holidays(self):
        # Town Meeting Day
        if self._year >= 1800:
            self._add_holiday("Town Meeting Day", self._get_nth_weekday_of_month(1, TUE, MAR))

        # Bennington Battle Day
        if self._year >= 1778:
            self._add_observed(self._add_holiday("Bennington Battle Day", AUG, 16))

    def _add_subdiv_wa_holidays(self):
        pass

    def _add_subdiv_wi_holidays(self):
        # Susan B. Anthony Day
        if self._year >= 1976:
            self._add_holiday("Susan B. Anthony Day", FEB, 15)

        if self._year >= 2012:
            # Christmas Eve
            self._add_christmas_eve_holiday()

            # New Year's Eve
            self._add_observed(self._add_new_years_eve("New Year's Eve"), after=False)

    def _add_subdiv_wv_holidays(self):
        # West Virginia Day
        if self._year >= 1927:
            self._add_observed(self._add_holiday("West Virginia Day", JUN, 20))

        # Election Day
        if self._year >= 2008 and self._year % 2 == 0:
            self._add_holiday(
                "Election Day",
                self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1),
            )

        # Day After Thanksgiving
        if self._year >= 1975:
            self._add_holiday(
                "Day After Thanksgiving",
                self._get_nth_weekday_of_month(4, THU, NOV) + td(days=+1),
            )

    def _add_subdiv_wy_holidays(self):
        pass


class US(UnitedStates):
    pass


class USA(UnitedStates):
    pass
