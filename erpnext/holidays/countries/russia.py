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

from holidays.calendars.gregorian import JAN, FEB, MAY, JUN, NOV
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Russia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Russia
    """

    country = "RU"
    default_language = "ru"
    supported_languages = ("en_US", "ru")

    special_holidays = {
        # Bridge days for 01/01/2023 and 08/01/2023.
        # src: https://www.consultant.ru/document/cons_doc_LAW_425407/
        2023: (
            (FEB, 24, tr("День защитника Отечества")),
            (MAY, 8, tr("День Победы")),
        ),
    }

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        if year <= 1990:
            return None
        super()._populate(year)

        if year <= 2004:
            # New Year's Day.
            name = tr("Новый год")
            self._add_new_years_day(name)
            if year >= 1993:
                self._add_new_years_day_two(name)
        else:
            # New Year Holidays.
            name = tr("Новогодние каникулы")
            for day in range(1, 6):
                self._add_holiday(name, JAN, day)
            if year >= 2013:
                self._add_holiday(name, JAN, 6)
                self._add_holiday(name, JAN, 8)

        # Christmas Day.
        self._add_christmas_day(tr("Рождество Христово"))

        if year >= 2002:
            # Defender of the Fatherland Day.
            self._add_holiday(tr("День защитника Отечества"), FEB, 23)

        # International Women's Day.
        self._add_womens_day(tr("Международный женский день"))

        name = (
            # Holiday of Spring and Labor.
            tr("Праздник Весны и Труда")
            if year >= 1992
            # International Workers' Solidarity Day.
            else tr("День международной солидарности трудящихся")
        )
        self._add_labor_day(name)
        if year <= 2004:
            self._add_labor_day_two(name)

        # Victory Day.
        self._add_world_war_two_victory_day(tr("День Победы"))

        if year >= 1992:
            self._add_holiday(
                # Russia Day.
                tr("День России") if year >= 2002
                # Day of the Adoption of the Declaration of Sovereignty of the Russian Federation.
                else tr(
                    "День принятия Декларации о государственном суверенитете Российской Федерации"
                ),
                JUN,
                12,
            )

        if year >= 2005:
            # Unity Day.
            self._add_holiday(tr("День народного единства"), NOV, 4)

        if year <= 2004:
            name = (
                # Day of consent and reconciliation.
                tr("День согласия и примирения")
                if year >= 1996
                # Anniversary of the Great October Socialist Revolution.
                else tr("Годовщина Великой Октябрьской социалистической революции")
            )
            self._add_holiday(name, NOV, 7)
            if year <= 1991:
                self._add_holiday(name, NOV, 8)


class RU(Russia):
    pass


class RUS(Russia):
    pass
