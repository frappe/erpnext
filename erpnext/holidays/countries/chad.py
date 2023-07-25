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

from holidays.calendars import _CustomIslamicCalendar
from holidays.calendars.gregorian import JAN, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays, IslamicHolidays


class Chad(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Chad
      - https://www.ilo.org/dyn/natlex/docs/ELECTRONIC/97323/115433/F-316075167/TCD-97323.pdf
    """

    country = "TD"
    special_holidays = {
        2021: (APR, 23, "Funeral of Idriss Déby Itno"),
    }

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=ChadIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        if self.observed and self._is_sunday(dt):
            self._add_holiday("%s (Observed)" % self[dt], dt + td(days=+1))

    def _populate(self, year):
        # On 11 August 1960, Chad gained independence from France.
        if year <= 1960:
            return None

        super()._populate(year)

        # New Year's Day.
        self._add_observed(self._add_new_years_day("New Year's Day"))

        # International Women's Day.
        self._add_observed(self._add_womens_day("International Women's Day"))

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        # Labour Day.
        self._add_observed(self._add_labor_day("Labour Day"))

        # Independence Day.
        self._add_observed(self._add_holiday("Independence Day", AUG, 11))

        # All Saints' Day.
        self._add_all_saints_day("All Saints' Day")

        # Republic Day.
        self._add_observed(self._add_holiday("Republic Day", NOV, 28))

        if year >= 1991:
            # Freedom and Democracy Day.
            self._add_observed(self._add_holiday("Freedom and Democracy Day", DEC, 1))

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Eid al-Fitr.
        self._add_eid_al_fitr_day("Eid al-Fitr")

        # Eid al-Adha.
        self._add_eid_al_adha_day("Eid al-Adha")

        # Mawlid.
        self._add_mawlid_day("Mawlid")


class TD(Chad):
    pass


class TCD(Chad):
    pass


class ChadIslamicCalendar(_CustomIslamicCalendar):
    EID_AL_ADHA_DATES = {
        2015: (SEP, 24),
        2016: (SEP, 13),
        2017: (SEP, 2),
        2018: (AUG, 22),
        2019: (AUG, 11),
        2020: (JUL, 31),
        2021: (JUL, 20),
        2022: (JUL, 9),
        2023: (JUN, 28),
    }

    EID_AL_FITR_DATES = {
        2015: (JUL, 18),
        2016: (JUL, 7),
        2017: (JUN, 26),
        2018: (JUN, 15),
        2019: (JUN, 4),
        2020: (MAY, 24),
        2021: (MAY, 13),
        2022: (MAY, 2),
        2023: (APR, 21),
    }

    MAWLID_DATES = {
        2015: ((JAN, 3), (DEC, 24)),
        2016: (DEC, 12),
        2017: (DEC, 1),
        2018: (NOV, 21),
        2019: (NOV, 9),
        2020: (OCT, 29),
        2021: (OCT, 18),
        2022: (OCT, 8),
    }
