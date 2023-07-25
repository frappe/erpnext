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

from holidays.calendars.gregorian import FEB, APR, JUN, AUG, SEP, OCT, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Kenya(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Kenya
    http://kenyaembassyberlin.de/Public-Holidays-in-Kenya.48.0.html
    https://www.officeholidays.com/holidays/kenya/moi-day
    """

    country = "KE"
    special_holidays = {
        2020: (FEB, 11, "President Moi Celebration of Life Day"),
        2022: (
            (APR, 29, "State Funeral for Former President Mwai Kibaki"),
            (AUG, 9, "Election Day"),
            (SEP, 10, "Day of Mourning for Queen Elizabeth II"),
            (SEP, 11, "Day of Mourning for Queen Elizabeth II"),
            (SEP, 12, "Day of Mourning for Queen Elizabeth II"),
            (SEP, 13, "Inauguration Day"),
        ),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        def _add_observed(dt: date, days: int = +1) -> None:
            if self.observed and self._is_sunday(dt):
                self._add_holiday("%s (Observed)" % self[dt], dt + td(days=days))

        if year <= 1962:
            return None

        super()._populate(year)

        # New Year's Day
        _add_observed(self._add_new_years_day("New Year's Day"))

        # Good Friday
        self._add_good_friday("Good Friday")

        # Easter Monday
        self._add_easter_monday("Easter Monday")

        # Labour Day
        _add_observed(self._add_labor_day("Labour Day"))

        if year >= 2010:
            # Mandaraka Day
            _add_observed(self._add_holiday("Madaraka Day", JUN, 1))

        if 2002 <= year <= 2009 or year >= 2018:
            _add_observed(
                # Utamaduni/Moi Day
                self._add_holiday("Utamaduni Day" if year >= 2021 else "Moi Day", OCT, 10)
            )

        _add_observed(
            # Mashuja/Kenyatta Day
            self._add_holiday("Mashujaa Day" if year >= 2010 else "Kenyatta Day", OCT, 20)
        )

        # Jamhuri Day
        _add_observed(self._add_holiday("Jamhuri Day", DEC, 12))

        # Christmas Day
        _add_observed(self._add_christmas_day("Christmas Day"), days=+2)

        # Boxing Day
        _add_observed(self._add_christmas_day_two("Boxing Day"))


class KE(Kenya):
    pass


class KEN(Kenya):
    pass
