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

from holidays.calendars.gregorian import FEB, MAY, JUN, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Nigeria(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Nigeria
    """

    country = "NG"
    special_holidays = {
        2019: (
            (FEB, 22, "Public Holiday for Elections"),
            (MAY, 29, "Presidential Inauguration Day"),
        ),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1978:
            return None

        super()._populate(year)
        observed_dates = set()

        # New Year's Day
        observed_dates.add(self._add_new_years_day("New Year's Day"))

        self._add_good_friday("Good Friday")
        self._add_easter_monday("Easter Monday")

        # Worker's day
        if year >= 1981:
            observed_dates.add(self._add_labor_day("Workers' Day"))

        # Democracy day moved around after its inception in 2000
        # Initally it fell on May 29th
        # In 2018 it was announced that the holiday
        # will move to June 12th from 2019
        if year >= 2000:
            observed_dates.add(
                self._add_holiday("Democracy Day", *((JUN, 12) if year >= 2019 else (MAY, 29)))
            )

        # Independence Day
        observed_dates.add(self._add_holiday("Independence Day", OCT, 1))

        # Christmas day
        observed_dates.add(self._add_christmas_day("Christmas Day"))

        # Boxing day
        observed_dates.add(self._add_christmas_day_two("Boxing Day"))

        # Eid al-Fitr - Feast Festive
        # This is an estimate
        # date of observance is announced yearly
        observed_dates.update(self._add_eid_al_fitr_day("Eid-el-Fitr"))
        observed_dates.update(self._add_eid_al_fitr_day_two("Eid-el-Fitr Holiday"))

        # Eid al-Adha - Scarfice Festive
        # This is an estimate
        # date of observance is announced yearly
        observed_dates.update(self._add_eid_al_adha_day("Eid-el-Kabir"))
        observed_dates.update(self._add_eid_al_adha_day_two("Eid-el-Kabir Holiday"))

        # Birthday of Prophet Muhammad
        observed_dates.update(self._add_mawlid_day("Eid-el-Mawlid"))

        # Observed holidays
        if self.observed and year >= 2016:
            for hol_date in sorted(observed_dates):
                if not self._is_weekend(hol_date):
                    continue
                obs_date = hol_date + td(days=+1)
                while self._is_weekend(obs_date) or obs_date in observed_dates:
                    obs_date += td(days=+1)
                for hol_name in self.get_list(hol_date):
                    observed_dates.add(self._add_holiday("%s (Observed)" % hol_name, obs_date))


class NG(Nigeria):
    pass


class NGA(Nigeria):
    pass
