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

from holidays.calendars.gregorian import MAY, JUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Luxembourg(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Luxembourg
    """

    country = "LU"
    default_language = "lb"
    supported_languages = ("de", "en_US", "fr", "lb", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Neijoerschdag"))

        # Easter Monday.
        self._add_easter_monday(tr("Ouschterméindeg"))

        # Labor Day.
        self._add_labor_day(tr("Dag vun der Aarbecht"))

        if year >= 2019:
            # Europe Day.
            self._add_holiday(tr("Europadag"), MAY, 9)

        # Ascension Day.
        self._add_ascension_thursday(tr("Christi Himmelfaart"))

        # Whit Monday.
        self._add_whit_monday(tr("Péngschtméindeg"))

        # National Day.
        self._add_holiday(tr("Nationalfeierdag"), JUN, 23)

        # Assumption Day.
        self._add_assumption_of_mary_day(tr("Léiffrawëschdag"))

        # All Saints' Day.
        self._add_all_saints_day(tr("Allerhellgen"))

        # Christmas Day.
        self._add_christmas_day(tr("Chrëschtdag"))

        # St. Stephen's Day.
        self._add_christmas_day_two(tr("Stiefesdag"))


class LU(Luxembourg):
    pass


class LUX(Luxembourg):
    pass
