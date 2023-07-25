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

from gettext import gettext as tr

from holidays.calendars.gregorian import FEB, MAR, MAY, JUN, JUL, SUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Lithuania(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Lithuania holidays.

    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Lithuania
    - https://www.kalendorius.today/
    """

    country = "LT"
    default_language = "lt"
    supported_languages = ("en_US", "lt", "uk")

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year) -> None:
        if year <= 1989:
            return None
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Naujųjų metų diena"))

        # Day of Restoration of the State of Lithuania.
        self._add_holiday(tr("Lietuvos valstybės atkūrimo diena"), FEB, 16)

        # Day of Restoration of Independence of Lithuania.
        self._add_holiday(tr("Lietuvos nepriklausomybės atkūrimo diena"), MAR, 11)

        # Easter.
        self._add_easter_sunday(tr("Šv. Velykos"))

        # Easter Monday.
        self._add_easter_monday(tr("Antroji šv. Velykų diena"))

        # International Workers' Day.
        self._add_labor_day(tr("Tarptautinė darbo diena"))

        # Mother's day. First Sunday in May.
        self._add_holiday(tr("Motinos diena"), self._get_nth_weekday_of_month(1, SUN, MAY))

        # Fathers's day. First Sunday in June.
        self._add_holiday(tr("Tėvo diena"), self._get_nth_weekday_of_month(1, SUN, JUN))

        if year >= 2003:
            # Day of Dew and Saint John.
            self._add_saint_johns_day(tr("Rasos ir Joninių diena"))

        if year >= 1991:
            self._add_holiday(
                # Statehood Day.
                tr(
                    "Valstybės (Lietuvos karaliaus Mindaugo karūnavimo) "
                    "ir Tautiškos giesmės diena"
                ),
                JUL,
                6,
            )

        # Assumption Day.
        self._add_assumption_of_mary_day(tr("Žolinė (Švč. Mergelės Marijos ėmimo į dangų diena)"))

        # All Saints' Day.
        self._add_all_saints_day(tr("Visų Šventųjų diena"))

        if year >= 2020:
            # All Souls' Day.
            self._add_all_souls_day(tr("Mirusiųjų atminimo (Vėlinių) diena"))

        # Christmas Eve.
        self._add_christmas_eve(tr("Kūčių diena"))

        # Christmas Day.
        self._add_christmas_day(tr("Šv. Kalėdų pirma diena"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Šv. Kalėdų antra diena"))


class LT(Lithuania):
    pass


class LTU(Lithuania):
    pass
