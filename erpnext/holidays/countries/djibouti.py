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

from holidays.calendars.gregorian import FRI, SAT, JUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import IslamicHolidays, InternationalHolidays

# Since Djibouti share most of it's holidays with other muslim countries,
# this class is just a copy of Egypt's.


class Djibouti(HolidayBase, IslamicHolidays, InternationalHolidays):
    # Holidays here are estimates, it is common for the day to be pushed
    # if falls in a weekend, although not a rule that can be implemented.
    # Holidays after 2020: the following four moving date holidays whose exact
    # date is announced yearly are estimated (and so denoted):
    # - Eid El Fetr*
    # - Eid El Adha*
    # - Isra wal Miraj*
    # - Moulad El Naby*
    # - Arafat*
    # *only if hijri-converter library is installed, otherwise a warning is
    #  raised that this holiday is missing. hijri-converter requires
    #  Python >= 3.6
    # is_weekend function is there, however not activated for accuracy.

    country = "DJ"
    weekend = {FRI, SAT}

    def __init__(self, *args, **kwargs):
        IslamicHolidays.__init__(self)
        InternationalHolidays.__init__(self)

        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day
        self._add_new_years_day("Nouvel an")

        # Labour Day
        self._add_labor_day("Fête du travail")

        # Fête de l'indépendance
        self._add_holiday("Fête de l'indépendance", JUN, 27)
        self._add_holiday("Fête de l'indépendance", JUN, 28)

        # Isra wal Miraj
        # The night journey of the prophet Muhammad
        self._add_isra_and_miraj_day("Isra wal Miraj")

        # Eid al-Fitr - Feast Festive
        self._add_eid_al_fitr_day("Eid al-Fitr")
        self._add_eid_al_fitr_day_two("Eid al-Fitr deuxième jour")

        # Arafat & Eid al-Adha - Scarfice Festive
        self._add_arafah_day("Arafat")
        self._add_eid_al_adha_day("Eid al-Adha")
        self._add_eid_al_adha_day_two("Eid al-Adha deuxième jour")

        # Islamic New Year - (hijari_year, 1, 1)
        self._add_islamic_new_year_day("Nouvel an musulman")

        # Prophet Muhammad's Birthday - (hijari_year, 3, 12)
        self._add_mawlid_day("Naissance du prophet Muhammad")


class DJ(Djibouti):
    pass


class DJI(Djibouti):
    pass
