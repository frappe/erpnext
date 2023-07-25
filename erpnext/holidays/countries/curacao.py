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

from holidays.calendars.gregorian import APR, MAY, JUL, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Curacao(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://loketdigital.gobiernu.cw/Loket/product/571960bbe1e5fe8712b10a1323630e70
    https://en.wikipedia.org/wiki/Public_holidays_in_Cura%C3%A7ao

    New Year's Eve (Vispu di Aña Nobo) is a half-day public holiday, though
    this isn't supported by Python Holidays so it won't be implemented.
    """

    country = "CW"
    default_language = "pap"
    supported_languages = ("en_US", "nl", "pap", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # 1954: Creation of the Netherlands Antilles.
        if year <= 1953:
            return None

        super()._populate(year)

        # Aña Nobo.
        # Status: In-Use.

        # New Year's Day
        self._add_new_years_day(tr("Aña Nobo"))

        # Dialuna despues di Carnaval Grandi.
        # Status: In-Use.
        # Started in 1947.

        # Carnival Monday
        self._add_ash_monday(tr("Dialuna despues di Carnaval Grandi"))

        # Bièrnèsantu.
        # Status: In-Use.

        # Good Friday
        self._add_good_friday(tr("Bièrnèsantu"))

        # Pasku di Resurekshon.
        # Status: In-Use

        # Easter Sunday
        self._add_easter_sunday(tr("Pasku di Resurekshon"))

        # Di dos dia di Pasku di Resurekshon.
        # Status: In-Use.

        # Easter Monday
        self._add_easter_monday(tr("Di dos dia di Pasku di Resurekshon"))

        # Dia di la Reina/Dia di Rey.
        # Status: In-Use.
        # Started under Queen Wilhelmina in 1891.
        # Queen Beatrix kept Queen Juliana's Birthday after her coronation.
        # Switched to Aña di Rey in 2014 for King Willem-Alexander.
        # Have its name changed again to Dia di Rey from 2021 onwards.

        # King's / Queen's Day
        name = (
            # King's Day.
            tr("Dia di Rey")
            if year >= 2014
            # Queen's Day.
            else tr("Dia di la Reina")
        )
        if year >= 2014:
            dt = date(year, APR, 27)
        else:
            dt = date(year, APR, 30)
        if self._is_sunday(dt):
            dt += td(days=-1) if year >= 1980 else td(days=+1)
        self._add_holiday(name, dt)

        # Dia di Obrero.
        # Status: In-Use.
        # If fall on Sunday, then this will be move to next working day.

        dt = date(year, MAY, 1)
        if self._is_sunday(dt) or (self._is_monday(dt) and year <= 1979):
            dt += td(days=+1)
        # Labor Day
        self._add_holiday(tr("Dia di Obrero"), dt)

        # Dia di Asenshon.
        # Status: In-Use.

        # Ascension Day
        self._add_ascension_thursday(tr("Dia di Asenshon"))

        # Dia di Himno i Bandera.
        # Status: In-Use.
        # Starts in 1984.

        if year >= 1984:
            # National Anthem and Flag Day
            self._add_holiday(tr("Dia di Himno i Bandera"), JUL, 2)

        # Dia di Pais Kòrsou / Dia di autonomia.
        # Status: In-Use.
        # Starts in 2010.

        if year >= 2010:
            # Curaçao Day
            self._add_holiday(tr("Dia di Pais Kòrsou"), OCT, 10)

        # Pasku di Nasementu.
        # Status: In-Use.

        # Christmas Day
        self._add_christmas_day(tr("Pasku di Nasementu"))

        # Di dos dia di Pasku di Nasementu.
        # Status: In-Use.

        # Second Day of Christmas
        self._add_christmas_day_two(tr("Di dos dia di Pasku di Nasementu"))


class CW(Curacao):
    pass


class CUW(Curacao):
    pass
