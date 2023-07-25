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
from gettext import gettext as tr

from holidays.calendars.gregorian import MAR, APR, AUG, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Hungary(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Hungary
    Codification dates:
      - https://hvg.hu/gazdasag/20170307_Megszavaztak_munkaszuneti_nap_lett_a_nagypentek  # noqa
      - https://www.tankonyvtar.hu/hu/tartalom/historia/92-10/ch01.html#id496839
    """

    country = "HU"
    default_language = "hu"
    supported_languages = ("en_US", "hu", "uk")

    def _add_observed(
        self, dt: date, since: int = 2010, before: bool = True, after: bool = True
    ) -> None:
        if not self.observed or dt.year < since:
            return None
        if self._is_tuesday(dt) and before:
            # Day off before
            self._add_holiday(self.tr("%s előtti pihenőnap") % self[dt], dt + td(days=-1))
        elif self._is_thursday(dt) and after:
            # Day off after
            self._add_holiday(self.tr("%s utáni pihenőnap") % self[dt], dt + td(days=+1))

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        name = self.tr("Újév")
        self._add_observed(self._add_new_years_day(name), before=False, since=2014)

        # The last day of the year is an observed day off if New Year's Day
        # falls on a Tuesday.
        if self.observed and self._is_monday(DEC, 31) and year >= 2014:
            self._add_holiday(self.tr("%s előtti pihenőnap") % name, DEC, 31)

        if 1945 <= year <= 1950 or year >= 1989:
            # National Day.
            self._add_observed(self._add_holiday(tr("Nemzeti ünnep"), MAR, 15))

        if year >= 2017:
            # Good Friday.
            self._add_good_friday(tr("Nagypéntek"))

        # Easter.
        self._add_easter_sunday(tr("Húsvét"))

        if year != 1955:
            # Easter Monday.
            self._add_easter_monday(tr("Húsvét Hétfő"))

        # Whit Sunday.
        self._add_whit_sunday(tr("Pünkösd"))

        if year <= 1952 or year >= 1992:
            # Whit Monday.
            self._add_whit_monday(tr("Pünkösdhétfő"))

        if year >= 1946:
            # Labor Day.
            name = tr("A Munka ünnepe")
            self._add_observed(self._add_labor_day(name))
            if 1950 <= year <= 1953:
                self._add_labor_day_two(name)

        self._add_observed(
            self._add_holiday(
                # Bread Day.
                tr("A kenyér ünnepe") if 1950 <= year <= 1989 else
                # State Foundation Day.
                tr("Az államalapítás ünnepe"),
                AUG,
                20,
            )
        )

        if year >= 1991:
            # National Day.
            self._add_observed(self._add_holiday(tr("Nemzeti ünnep"), OCT, 23))

        if year >= 1999:
            # All Saints' Day.
            self._add_observed(self._add_all_saints_day(tr("Mindenszentek")))

        # Christmas Day.
        self._add_christmas_day(tr("Karácsony"))

        if year != 1955:
            self._add_observed(
                # Second Day of Christmas.
                self._add_christmas_day_two(tr("Karácsony másnapja")),
                since=2013,
                before=False,
            )

        # Soviet era.
        if 1950 <= year <= 1989:
            # Proclamation of Soviet Republic Day.
            self._add_holiday(tr("A Tanácsköztársaság kikiáltásának ünnepe"), MAR, 21)

            # Liberation Day.
            self._add_holiday(tr("A felszabadulás ünnepe"), APR, 4)

            if year not in {1956, 1989}:
                # Great October Socialist Revolution Day.
                self._add_holiday(tr("A nagy októberi szocialista forradalom ünnepe"), NOV, 7)


class HU(Hungary):
    pass


class HUN(Hungary):
    pass
