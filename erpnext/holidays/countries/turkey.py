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

from holidays.calendars.gregorian import APR, MAY, JUL, AUG, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import IslamicHolidays, InternationalHolidays


class Turkey(HolidayBase, IslamicHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Turkey
    """

    country = "TR"

    def __init__(self, *args, **kwargs):
        IslamicHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # 1st of Jan.
        self._add_new_years_day("New Year's Day")

        # 23rd of Apr.
        self._add_holiday("National Sovereignty and Children's Day", APR, 23)

        # 1st of May.
        self._add_labor_day("Labour Day")

        # 19th of May.
        self._add_holiday("Commemoration of Ataturk, Youth and Sports Day", MAY, 19)

        # 15th of Jul.
        # Became a national holiday after 15 Jul 2016 coup d'etat attempt.
        if year > 2016:
            self._add_holiday("Democracy and National Unity Day", JUL, 15)

        # 30th of Aug.
        self._add_holiday("Victory Day", AUG, 30)

        # 29th of Oct.
        self._add_holiday("Republic Day", OCT, 29)

        # Ramadan Feast.
        # Date of observance is announced yearly. This is an estimate.
        self._add_eid_al_fitr_day("Ramadan Feast")
        self._add_eid_al_fitr_day_two("Ramadan Feast Holiday")
        self._add_eid_al_fitr_day_three("Ramadan Feast Holiday")

        # Sacrifice Feast.
        # Date of observance is announced yearly, This is an estimate.
        self._add_eid_al_adha_day("Sacrifice Feast")
        self._add_eid_al_adha_day_two("Sacrifice Feast Holiday")
        self._add_eid_al_adha_day_three("Sacrifice Feast Holiday")
        self._add_eid_al_adha_day_four("Sacrifice Feast Holiday")


class TR(Turkey):
    pass


class TUR(Turkey):
    pass
