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
    MAY,
    JUN,
    JUL,
    AUG,
    SEP,
    OCT,
    NOV,
    DEC,
    MON,
    THU,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class NewYorkStockExchange(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Official regulations:
    - https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf
    - https://www.nyse.com/markets/hours-calendars
    Historical data:
    - s3.amazonaws.com/armstrongeconomics-wp/2013/07/NYSE-Closings.pdf
    """

    market = "NYSE"
    special_holidays = {
        1888: (
            (MAR, 12, "Blizzard of 1888"),
            (MAR, 13, "Blizzard of 1888"),
            (NOV, 30, "Thanksgiving Friday 1888"),
        ),
        1889: (
            (APR, 29, "Centennial of Washington Inauguration"),
            (APR, 30, "Centennial of Washington Inauguration"),
            (MAY, 1, "Centennial of Washington Inauguration"),
        ),
        1892: (
            (OCT, 12, "Columbian Celebration"),
            (OCT, 21, "Columbian Celebration"),
        ),
        1893: (APR, 27, "Columbian Celebration"),
        1897: (APR, 27, "Grant's Birthday"),
        1898: (MAY, 4, "Charter Day"),
        1899: (
            (MAY, 29, "Monday before Decoration Day"),
            (JUL, 3, "Monday before Independence Day"),
            (SEP, 29, "Admiral Dewey Celebration"),
        ),
        1900: (DEC, 24, "Christmas Eve"),
        1901: (
            (JUL, 5, "Friday after Independence Day"),
            (SEP, 19, "Funeral of President McKinley"),
        ),
        1903: (APR, 22, "Opening of new NYSE building"),
        1917: (JUN, 5, "Draft Registration Day"),
        1918: (
            (JAN, 28, "Heatless Day"),
            (FEB, 4, "Heatless Day"),
            (FEB, 11, "Heatless Day"),
            (JUN, 14, "Heatless Day"),
            (SEP, 12, "Draft Registration Day"),
            (NOV, 11, "Armistice Day"),
        ),
        1919: (
            (MAR, 25, "Homecoming Day for 27th Division"),
            (MAY, 6, "Parade Day for 77th Division"),
            (SEP, 10, "Return of General Pershing"),
        ),
        1923: (
            (AUG, 3, "Death of President Warren G. Harding"),
            (AUG, 10, "Funeral of President Warren G. Harding"),
        ),
        1927: (JUN, 13, "Parade for Colonel Charles Lindbergh"),
        1929: (NOV, 29, "Catch Up Day"),
        1933: (
            (MAR, 6, "Special Bank Holiday"),
            (MAR, 7, "Special Bank Holiday"),
            (MAR, 8, "Special Bank Holiday"),
            (MAR, 9, "Special Bank Holiday"),
            (MAR, 10, "Special Bank Holiday"),
            (MAR, 13, "Special Bank Holiday"),
            (MAR, 14, "Special Bank Holiday"),
        ),
        1945: (
            (AUG, 15, "V-J Day (WWII)"),
            (AUG, 16, "V-J Day (WWII)"),
            (DEC, 24, "Christmas Eve"),
        ),
        1954: (DEC, 24, "Christmas Eve"),
        1956: (DEC, 24, "Christmas Eve"),
        1958: (DEC, 26, "Day after Christmas"),
        1961: (MAY, 29, "Day before Decoration Day"),
        1963: (NOV, 25, "Funeral of President John F. Kennedy"),
        1965: (DEC, 24, "Christmas Eve"),
        1968: (
            (APR, 9, "Day of Mourning for Martin Luther King Jr."),
            (JUL, 5, "Day after Independence Day"),
        ),
        1969: (
            (FEB, 10, "Heavy Snow"),
            (MAR, 31, "Funeral of President Dwight D. Eisenhower"),
            (JUL, 21, "National Participation in Lunar Exploration"),
        ),
        1972: (DEC, 28, "Funeral for President Harry S. Truman"),
        1973: (JAN, 25, "Funeral for President Lyndon B. Johnson"),
        1977: (JUL, 14, "Blackout in New Yor City"),
        1985: (SEP, 27, "Hurricane Gloria"),
        1994: (APR, 27, "Funeral for President Richard M. Nixon"),
        2001: (
            (SEP, 11, "Closed for Sept 11, 2001 Attacks"),
            (SEP, 12, "Closed for Sept 11, 2001 Attacks"),
            (SEP, 13, "Closed for Sept 11, 2001 Attacks"),
            (SEP, 14, "Closed for Sept 11, 2001 Attacks"),
        ),
        2004: (JUN, 11, "Day of Mourning for President Ronald W. Reagan"),
        2007: (JAN, 2, "Day of Mourning for President Gerald R. Ford"),
        2012: (
            (OCT, 29, "Hurricane Sandy"),
            (OCT, 30, "Hurricane Sandy"),
        ),
        2018: (DEC, 5, "Day of Mourning for President George H.W. Bush"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed_holiday(self, name: str, dt: date) -> None:
        if self._is_saturday(dt):
            dt += td(days=-1)
            name = f"{name} (Observed)"
        elif self._is_sunday(dt):
            dt += td(days=+1)
            name = f"{name} (Observed)"

        self._add_holiday(name, dt)

    def _populate(self, year):
        super()._populate(year)

        # New Year Day.
        jan_1 = date(year, JAN, 1)
        if not self._is_saturday(jan_1):
            self._add_observed_holiday("New Year's Day", jan_1)

        # https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf
        # As per Rule 7.2.: check if next year's NYD falls on Saturday and
        # needs to be observed on Friday (Dec 31 of previous year).
        dec_31 = date(year, DEC, 31)
        if self._is_friday(dec_31):
            self._add_observed_holiday("New Year's Day", dec_31 + td(days=+1))

        # MLK, 3rd Monday of January.
        if year >= 1998:
            self._add_holiday(
                "Martin Luther King Jr. Day", self._get_nth_weekday_of_month(3, MON, JAN)
            )

        # LINCOLN BIRTHDAY: observed 1896 - 1953 and 1968, Feb 12 (observed)
        if 1896 <= year <= 1953 or year == 1968:
            self._add_observed_holiday("Lincoln's Birthday", date(year, FEB, 12))

        # WASHINGTON'S BIRTHDAY: Feb 22 (obs) until 1971, then 3rd Mon of Feb
        self._add_observed_holiday(
            "Washington's Birthday",
            date(year, FEB, 22) if year <= 1970 else self._get_nth_weekday_of_month(3, MON, FEB),
        )

        # GOOD FRIDAY - closed every year except 1898, 1906, and 1907
        if year not in {1898, 1906, 1907}:
            self._add_good_friday("Good Friday")

        # MEM DAY (May 30) - closed every year since 1873
        # last Mon in May since 1971
        if year >= 1873:
            dt = (
                date(year, MAY, 30)
                if year <= 1970
                else self._get_nth_weekday_of_month(-1, MON, MAY)
            )
            self._add_observed_holiday("Memorial Day", dt)

        # FLAG DAY: June 14th 1916 - 1953
        if 1916 <= year <= 1953:
            self._add_observed_holiday("Flag Day", date(year, JUN, 14))

        # JUNETEENTH: since 2021
        if year >= 2021:
            self._add_observed_holiday("Juneteenth National Independence Day", date(year, JUN, 19))

        # INDEPENDENCE DAY (July 4) - history suggests closed every year
        self._add_observed_holiday("Independence Day", date(year, JUL, 4))

        # LABOR DAY - first mon in Sept, since 1887
        if year >= 1887:
            self._add_holiday("Labor Day", self._get_nth_weekday_of_month(1, MON, SEP))

        # COLUMBUS DAY/INDIGENOUS PPL DAY: Oct 12 - closed 1909-1953
        if 1909 <= year <= 1953:
            self._add_observed_holiday("Columbus Day", date(year, OCT, 12))

        # ELECTION DAY: Tuesday after first Monday in November (2 U.S. Code §7)
        # closed until 1969, then closed pres years 1972-80
        if year <= 1968 or year in {1972, 1976, 1980}:
            self._add_holiday(
                "Election Day", self._get_nth_weekday_of_month(1, MON, NOV) + td(days=+1)
            )

        # VETERAN'S DAY: Nov 11 - closed 1918, 1921, 1934-1953
        if year in {1918, 1921} or 1934 <= year <= 1953:
            self._add_observed_holiday("Veteran's Day", date(year, NOV, 11))

        # THXGIVING DAY: 4th Thurs in Nov - closed every year
        self._add_holiday("Thanksgiving Day", self._get_nth_weekday_of_month(4, THU, NOV))

        # XMAS DAY: Dec 25th - every year
        self._add_observed_holiday("Christmas Day", date(year, DEC, 25))

        # Special holidays.
        if year == 1914:
            # Beginning of WWI.
            begin = date(year, JUL, 31)
            end = date(year, NOV, 27)
            for dt in (begin + td(days=n) for n in range((end - begin).days + 1)):
                if self._is_weekend(dt) or dt in self:
                    continue
                self._add_holiday("World War I", dt)
        elif year == 1968:
            begin = date(year, JUN, 12)
            end = date(year, DEC, 24)
            # Wednesday special holiday.
            for dt in (begin + td(days=n) for n in range(0, (end - begin).days + 1, 7)):
                self._add_holiday("Paper Crisis", dt)


class XNYS(NewYorkStockExchange):
    pass


class NYSE(NewYorkStockExchange):
    pass
