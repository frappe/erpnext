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

from holidays.calendars.gregorian import MAY, JUN, AUG, SEP
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class ElSalvador(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://www.transparencia.gob.sv/institutions/gd-usulutan/documents/192280/download
    - https://www.timeanddate.com/holidays/el-salvador
    - https://www.officeholidays.com/countries/el-salvador
    """

    country = "SV"
    subdivisions = (
        "AH",  # Ahuachapán
        "CA",  # Cabañas
        "CH",  # Chalatenango
        "CU",  # Cuscatlán
        "LI",  # La Libertad
        "MO",  # Morazán
        "PA",  # La Paz
        "SA",  # Santa Ana
        "SM",  # San Miguel
        "SO",  # Sonsonate
        "SS",  # San Salvador
        "SV",  # San Vicente
        "UN",  # La Unión
        "US",  # Usulután
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("New Year's Day")

        # Maundy Thursday.
        self._add_holy_thursday("Maundy Thursday")

        # Good Friday.
        self._add_good_friday("Good Friday")

        # Holy Saturday.
        self._add_holy_saturday("Holy Saturday")

        # Labor Day.
        self._add_labor_day("Labor Day")

        if year >= 2016:
            # Legislative Decree #399 from Apr 14, 2016
            # Mothers' Day.
            self._add_holiday("Mothers' Day", MAY, 10)

        if year >= 2013:
            # Legislative Decree #208 from Jun 17, 2012
            # Fathers' Day.
            self._add_holiday("Fathers' Day", JUN, 17)

        # Feast of San Salvador.
        self._add_holiday("Feast of San Salvador", AUG, 6)

        # Independence Day.
        self._add_holiday("Independence Day", SEP, 15)

        # All Souls' Day.
        self._add_all_souls_day("All Souls' Day")

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

    def _add_subdiv_ss_holidays(self):
        # San Salvador Day 1.
        self._add_holiday("San Salvador Day 1", AUG, 3)

        # San Salvador Day 2.
        self._add_holiday("San Salvador Day 2", AUG, 5)


class SV(ElSalvador):
    pass


class SLV(ElSalvador):
    pass
