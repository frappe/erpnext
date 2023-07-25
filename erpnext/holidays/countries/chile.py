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
from typing import Tuple

from holidays.calendars.gregorian import MAY, JUN, JUL, AUG, SEP, OCT, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Chile(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://www.feriados.cl
    - http://www.feriadoschilenos.cl/ (excellent history)
    - https://es.wikipedia.org/wiki/Anexo:D%C3%ADas_feriados_en_Chile
    - Law 2.977 (established official Chile holidays in its current form)
    - Law 20.983 (Day after New Year's Day, if it's a Sunday)
    - Law 19.668 (floating Monday holiday)
    - Law 19.668 (Corpus Christi)
    - Law 2.200, (Labour Day)
    - Law 18.018 (Labour Day renamed)
    - Law 16.840, Law 18.432 (Saint Peter and Saint Paul)
    - Law 20.148 (Day of Virgin of Carmen)
    - Law 18.026 (Day of National Liberation)
    - Law 19.588, Law 19.793 (Day of National Unity)
    - Law 20.983 (National Holiday Friday preceding Independence Day)
    - Law 20.215 (National Holiday Monday preceding Independence Day)
    - Law 20.215 (National Holiday Friday following Army Day)
    - Decree-law 636, Law 8.223
    - Law 3.810 (Columbus Day)
    - Law 20.299 (National Day of the Evangelical and Protestant Churches)
    - Law 20.663 (Región de Arica y Parinacota)
    - Law 20.678 (Región de Ñuble)
    """

    country = "CL"
    default_language = "es"
    special_holidays = {
        # National Holiday.
        2022: (SEP, 16, tr("Feriado nacional")),
    }
    subdivisions = (
        "AI",
        "AN",
        "AP",
        "AR",
        "AT",
        "BI",
        "CO",
        "LI",
        "LL",
        "LR",
        "MA",
        "ML",
        "NB",
        "RM",
        "TA",
        "VS",
    )
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _move_holiday(self, dt: date) -> None:
        if self._year <= 1999 or self._is_monday(dt) or self._is_weekend(dt):
            return None
        self._add_holiday(
            self[dt],
            self._get_nth_weekday_from(1, MON, dt)
            if self._is_friday(dt)
            else self._get_nth_weekday_from(-1, MON, dt),
        )
        self.pop(dt)

    def _populate(self, year):
        if year <= 1914:
            return None

        super()._populate(year)

        # New Year's Day.
        jan_1 = self._add_new_years_day(tr("Año Nuevo"))
        if year >= 2017 and self._is_sunday(jan_1):
            self._add_new_years_day_two(tr("Feriado nacional"))

        # Good Friday.
        self._add_good_friday(tr("Viernes Santo"))

        # Holy Saturday.
        self._add_holy_saturday(tr("Sábado Santo"))

        if year <= 1967:
            # Ascension of Jesus.
            self._add_ascension_thursday(tr("Ascensión del Señor"))

        if year <= 1967 or 1987 <= year <= 2006:
            self._add_holiday(
                # Corpus Christi.
                tr("Corpus Christi"),
                self._easter_sunday + td(days=+60 if year <= 1999 else +57),
            )

        if year >= 1932:
            # Labour Day.
            self._add_labor_day(tr("Día Nacional del Trabajo"))

        # Naval Glories Day.
        self._add_holiday(tr("Día de las Glorias Navales"), MAY, 21)

        if year >= 2021:
            self._add_holiday(
                # National Day of Indigenous Peoples.
                tr("Día Nacional de los Pueblos Indígenas"),
                *((JUN, 21) if year == 2021 else self._summer_solstice_date),
            )

        if year <= 1967 or year >= 1986:
            # Saint Peter and Saint Paul.
            self._move_holiday(self._add_saints_peter_and_paul_day(tr("San Pedro y San Pablo")))

        if year >= 2007:
            # Day of Virgin of Carmen.
            self._add_holiday(tr("Virgen del Carmen"), JUL, 16)

        # Assumption of Mary.
        self._add_assumption_of_mary_day(tr("Asunción de la Virgen"))

        if 1981 <= year <= 1998:
            # Day of National Liberation.
            self._add_holiday(tr("Día de la Liberación Nacional"), SEP, 11)
        elif 1999 <= year <= 2001:
            self._add_holiday(
                # Day of National Unity.
                tr("Día de la Unidad Nacional"),
                self._get_nth_weekday_of_month(1, MON, SEP),
            )

        if year >= 2017 and self._is_saturday(SEP, 18):
            # National Holiday.
            self._add_holiday(tr("Fiestas Patrias"), SEP, 17)

        if year >= 2007 and self._is_tuesday(SEP, 18):
            self._add_holiday(tr("Fiestas Patrias"), SEP, 17)

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), SEP, 18)

        # Army Day.
        self._add_holiday(tr("Día de las Glorias del Ejército"), SEP, 19)

        if year >= 2008 and self._is_thursday(SEP, 19):
            self._add_holiday(tr("Fiestas Patrias"), SEP, 20)

        if 1932 <= year <= 1944:
            self._add_holiday(tr("Fiestas Patrias"), SEP, 20)

        if year >= 1922 and year != 1973:
            name = (
                # Meeting of Two Worlds' Day.
                tr("Día del Encuentro de dos Mundos")
                if year >= 2000
                # Columbus Day.
                else tr("Día de la Raza")
            )
            self._move_holiday(self._add_columbus_day(name))

        if year >= 2008:
            dt = date(year, OCT, 31)
            # This holiday is moved to the preceding Friday if it falls on a Tuesday,
            # or to the following Friday if it falls on a Wednesday.
            if self._is_wednesday(dt):
                dt += td(days=+2)
            elif self._is_tuesday(dt):
                dt += td(days=-4)
            # National Day of the Evangelical and Protestant Churches.
            self._add_holiday(tr("Día Nacional de las Iglesias Evangélicas y Protestantes"), dt)

        # All Saints Day.
        self._add_all_saints_day(tr("Día de Todos los Santos"))

        # Immaculate Conception.
        self._add_immaculate_conception_day(tr("La Inmaculada Concepción"))

        if 1944 <= year <= 1988:
            # Christmas Eve.
            self._add_christmas_eve(tr("Víspera de Navidad"))

        # Christmas.
        self._add_christmas_day(tr("Navidad"))

    def _add_subdiv_ap_holidays(self):
        if self._year >= 2013:
            # Assault and Capture of Cape Arica.
            self._add_holiday(tr("Asalto y Toma del Morro de Arica"), JUN, 7)

    def _add_subdiv_nb_holidays(self):
        if self._year >= 2014:
            # Nativity of Bernardo O'Higgins (Chillán and Chillán Viejo communes)
            name = tr("Nacimiento del Prócer de la Independencia (Chillán y Chillán Viejo)")
            self._add_holiday(name, AUG, 20)

    @property
    def _summer_solstice_date(self) -> Tuple[int, int]:
        day = 20
        if (self._year % 4 > 1 and self._year <= 2046) or (
            self._year % 4 > 2 and self._year <= 2075
        ):
            day = 21
        return JUN, day


class CL(Chile):
    pass


class CHL(Chile):
    pass
