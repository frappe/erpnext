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

from holidays.calendars.gregorian import JAN, MAR, APR, AUG
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Aruba(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://www.government.aw/information-public-services/hiring-people_47940/item/holidays_43823.html  # noqa: E501
    https://www.overheid.aw/informatie-dienstverlening/ondernemen-en-werken-subthemas_46970/item/feestdagen_37375.html  # noqa: E501
    https://www.gobierno.aw/informacion-tocante-servicio/haci-negoshi-y-traha-sub-topics_47789/item/dia-di-fiesta_41242.html  # noqa: E501
    https://www.visitaruba.com/about-aruba/national-holidays-and-celebrations/
    https://www.arubatoday.com/we-celebrate-our-national-hero-betico-croes/
    https://www.caribbeannewsglobal.com/carnival-monday-remains-a-festive-day-in-aruba/  # noqa: E501
    https://www.aruba.com/us/calendar/national-anthem-and-flag-day
    """

    country = "AW"
    default_language = "pap"
    supported_languages = ("en_US", "nl", "pap", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # AUG 1947: Autonomous State status in the Kingdom of the Netherlands.
        if year <= 1946:
            return None

        super()._populate(year)

        # Aña Nobo.
        # Status: In-Use.

        # New Year's Day
        self._add_new_years_day(tr("Aña Nobo"))

        # Dia Di Betico.
        # Status: In-Use.
        # Started in 1989.

        if year >= 1989:
            # Betico Day
            self._add_holiday(tr("Dia di Betico"), JAN, 25)

        # Dialuna prome cu diaranson di shinish.
        # Status: In-Use.
        # Starts as a public holiday from 1956 onwards.
        # Event cancelled but remain a holiday in 2021.
        # Have its name changed from 2023 onwards.

        if year >= 1956:
            self._add_ash_monday(
                # Carnival Monday
                tr("Dialuna despues di Carnaval Grandi")
                if year <= 2022
                # Monday before Ash Wednesday
                else tr("Dialuna prome cu diaranson di shinish")
            )

        # Dia di Himno y Bandera.
        # Status: In-Use.
        # Started in 1976.

        if year >= 1976:
            # National Anthem and Flag Day
            self._add_holiday(tr("Dia di Himno y Bandera"), MAR, 18)

        # Bierna Santo.
        # Status: In-Use.

        # Good Friday
        self._add_good_friday(tr("Bierna Santo"))

        # Di dos dia di Pasco di Resureccion.
        # Status: In-Use.

        # Easter Monday
        self._add_easter_monday(tr("Di dos dia di Pasco di Resureccion"))

        # Aña di La Reina/Aña di Rey/Dia di Rey.
        # Status: In-Use.
        # Started under Queen Wilhelmina in 1891.
        # Queen Beatrix kept Queen Juliana's Birthday after her coronation.
        # Switched to Aña di Rey in 2014 for King Willem-Alexander.
        # Have its name changed again to Dia di Rey from 2021 onwards.

        # King's / Queen's Day
        name = (
            # King's Day.
            tr("Dia di Rey")
            if year >= 2021
            else (
                # King's Day.
                tr("Aña di Rey")
                if year >= 2014
                # Queen's Day.
                else tr("Aña di La Reina")
            )
        )
        if year >= 2014:
            dt = date(year, APR, 27)
        elif year >= 1949:
            dt = date(year, APR, 30)
        else:
            dt = date(year, AUG, 31)
        if self._is_sunday(dt):
            dt += td(days=-1) if year >= 1980 else td(days=+1)
        self._add_holiday(name, dt)

        # Dia di Labor/Dia di Obrero.
        # Status: In-Use.

        # Labor Day
        self._add_labor_day(tr("Dia di Obrero"))

        # Dia di Asuncion.
        # Status: In-Use.

        # Ascension Day
        self._add_ascension_thursday(tr("Dia di Asuncion"))

        # Pasco di Nacemento.
        # Status: In-Use.

        # Christmas Day
        self._add_christmas_day(tr("Pasco di Nacemento"))

        # Di dos dia di Pasco di Nacemento.
        # Status: In-Use.

        # Second Day of Christmas
        self._add_christmas_day_two(tr("Di dos dia di Pasco di Nacemento"))


class AW(Aruba):
    pass


class ABW(Aruba):
    pass
