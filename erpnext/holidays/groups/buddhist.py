#  python-holidays
#  ---------------
#  A fast, efficient Python library for generating country, province and state
#  specific sets of holidays on the fly. It aims to make determining whether a
#  specific date is a holiday as fast and flexible as possible.
#
#  Authors: dr-prodigy <maurizio.montel@gmail.com> (c) 2017-2022
#           ryanss <ryanssdev@icloud.com> (c) 2014-2017
#  Website: https://github.com/dr-prodigy/python-holidays
#  License: MIT (see LICENSE file)

from datetime import date
from typing import Tuple, Optional

from holidays.calendars import _BuddhistLunisolar


class BuddhistCalendarHolidays:
    """
    Buddhist lunisolar calendar holidays.
    """

    def __init__(self, calendar=_BuddhistLunisolar(), show_estimated=False) -> None:
        self._buddhist_calendar = calendar
        self._show_estimated = show_estimated

    def _add_buddhist_calendar_holiday(
        self, name: str, hol_date: Tuple[date, bool]
    ) -> Optional[date]:
        """
        Add Buddhist calendar holiday.

        Adds customizable estimation label to holiday name if holiday date
        is an estimation.
        """
        estimated_label = getattr(self, "estimated_label", "%s* (*estimated)")
        dt, is_estimated = hol_date

        return self._add_holiday(
            self.tr(estimated_label) % self.tr(name)
            if is_estimated and self._show_estimated
            else name,
            dt,
        )

    def _add_vesak(self, name) -> Optional[date]:
        """
        Add Vesak (15th day of the 4th lunar month).

        Vesak for Thailand, Laos, Singapore and Indonesia.
        https://en.wikipedia.org/wiki/Vesak
        """
        return self._add_buddhist_calendar_holiday(
            name, self._buddhist_calendar.vesak_date(self._year)
        )

    def _add_vesak_may(self, name) -> Optional[date]:
        """
        Add Vesak (on the day of the first full moon in May
        in the Gregorian calendar).

        Vesak for Sri Lanka, Nepal, India, Bangladesh and Malaysia.
        https://en.wikipedia.org/wiki/Vesak
        """
        return self._add_buddhist_calendar_holiday(
            name, self._buddhist_calendar.vesak_may_date(self._year)
        )
