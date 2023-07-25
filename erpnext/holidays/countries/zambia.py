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

from holidays.calendars.gregorian import MAR, APR, JUL, AUG, SEP, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Zambia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.officeholidays.com/countries/zambia/
    https://www.timeanddate.com/holidays/zambia/
    https://en.wikipedia.org/wiki/Public_holidays_in_Zambia
    https://www.parliament.gov.zm/sites/default/files/documents/acts/Public%20Holidays%20Act.pdf
    """

    country = "ZM"
    special_holidays = {
        2016: (
            (AUG, 11, "General elections and referendum"),
            (SEP, 13, "Inauguration ceremony of President-elect and Vice President-elect"),
        ),
        2018: (
            (MAR, 9, "Public holiday"),
            (JUL, 26, "Lusaka mayoral and other local government elections"),
        ),
        2021: (
            (JUL, 2, "Memorial service for Kenneth Kaunda"),
            (JUL, 7, "Funeral of Kenneth Kaunda"),
            (AUG, 12, "General elections"),
            (AUG, 13, "Counting in general elections"),
            (AUG, 24, "Presidential inauguration"),
        ),
        2022: (MAR, 18, "Funeral of Rupiah Banda"),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        # whenever a public holiday falls on a Sunday,
        # it rolls over to the following Monday
        if self.observed and self._is_sunday(dt):
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        # Observed since 1965
        if year <= 1964:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_observed(self._add_new_years_day("New Year's Day"))

        if year >= 1991:
            self._add_observed(
                # International Women's Day.
                self._add_womens_day("International Women's Day")
            )

        # Youth Day.
        self._add_observed(self._add_holiday("Youth Day", MAR, 12))

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Holy Saturday.
        self._add_holy_saturday("Holy Saturday")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        if year >= 2022:
            # Kenneth Kaunda Day.
            self._add_observed(self._add_holiday("Kenneth Kaunda Day", APR, 28))

        # Labour Day.
        self._add_observed(self._add_labor_day("Labour Day"))

        # Africa Freedom Day.
        self._add_observed(self._add_africa_day("Africa Freedom Day"))

        first_mon_of_july = self._add_holiday(
            # Heroes' Day.
            "Heroes' Day",
            self._get_nth_weekday_of_month(1, MON, JUL),
        )

        # Unity Day.
        self._add_holiday("Unity Day", first_mon_of_july + td(days=+1))

        # Farmers' Day.
        self._add_holiday("Farmers' Day", self._get_nth_weekday_of_month(1, MON, AUG))

        if year >= 2015:
            # National Prayer Day.
            self._add_observed(self._add_holiday("National Prayer Day", OCT, 18))

        # Independence Day.
        self._add_observed(self._add_holiday("Independence Day", OCT, 24))

        # Christmas Day.
        self._add_observed(self._add_christmas_day("Christmas Day"))


class ZM(Zambia):
    pass


class ZMB(Zambia):
    pass
