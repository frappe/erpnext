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

from holidays.calendars.gregorian import JUL, AUG, NOV, MON
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Colombia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Colombia has 18 holidays. The establishing of these are by:
    Ley 35 de 1939 (DEC 4): https://bit.ly/3PJwk7B
    Decreto 2663 de 1950 (AUG 5): https://bit.ly/3PJcut8
    Decreto 3743 de 1950 (DEC 20): https://bit.ly/3B9Otr3
    Ley 51 de 1983 (DEC 6): https://bit.ly/3aSobiB
    """

    country = "CO"
    default_language = "es"
    supported_languages = ("en_US", "es", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _move_holiday(self, dt: date) -> None:
        """
        On the 6th of December 1983, the government of Colombia declared which
        holidays are to take effect, and also clarified that a subset of them
        are to take place the next Monday if they do not fall on a Monday.
        This law is "Ley 51 de 1983" which translates to law 51 of 1983.
        Link: https://bit.ly/3PtPi2e
        A few links below to calendars from the 1980s to demonstrate this law
        change. In 1984 some calendars still use the old rules, presumably
        because they were printed prior to the declaration of law change.
        1981: https://bit.ly/3BbgKOc
        1982: https://bit.ly/3BdbhWW
        1984: https://bit.ly/3PqGxWU
        1984: https://bit.ly/3B7ogt8
        """

        if self.observed and not self._is_monday(dt) and self._year >= 1984:
            self._add_holiday(
                self.tr("%s (Observado)") % self[dt], self._get_nth_weekday_from(1, MON, dt)
            )
            self.pop(dt)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Año Nuevo"))

        if year >= 1951:
            # Epiphany.
            self._move_holiday(self._add_epiphany_day(tr("Día de los Reyes Magos")))

            # Saint Joseph's Day.
            self._move_holiday(self._add_saint_josephs_day(tr("Día de San José")))

            # Maundy Thursday.
            self._add_holy_thursday(tr("Jueves Santo"))

            # Good Friday.
            self._add_good_friday(tr("Viernes Santo"))

            # Ascension of Jesus.
            self._move_holiday(self._add_ascension_thursday(tr("Ascensión del señor")))

            # Corpus Christi.
            self._move_holiday(self._add_corpus_christi_day(tr("Corpus Christi")))

        # Labor Day.
        self._add_labor_day(tr("Día del Trabajo"))

        if year >= 1984:
            self._move_holiday(
                # Sacred Heart.
                self._add_holiday(tr("Sagrado Corazón"), self._easter_sunday + td(days=+68))
            )

        if year >= 1951:
            # Saint Peter and Saint Paul's Day.
            self._move_holiday(self._add_saints_peter_and_paul_day(tr("San Pedro y San Pablo")))

        # Independence Day.
        self._add_holiday(tr("Día de la Independencia"), JUL, 20)

        # Battle of Boyaca.
        self._add_holiday(tr("Batalla de Boyacá"), AUG, 7)

        if year >= 1951:
            # Assumption of Mary.
            self._move_holiday(self._add_assumption_of_mary_day(tr("La Asunción")))

        # Columbus Day.
        self._move_holiday(self._add_columbus_day(tr("Día de la Raza")))

        if year >= 1951:
            # All Saints' Day.
            self._move_holiday(self._add_all_saints_day(tr("Día de Todos los Santos")))

        self._move_holiday(
            # Independence of Cartagena.
            self._add_holiday(tr("Independencia de Cartagena"), NOV, 11)
        )

        if year >= 1951:
            # Immaculate Conception.
            self._add_immaculate_conception_day(tr("La Inmaculada Concepción"))

        # Christmas.
        self._add_christmas_day(tr("Navidad"))


class CO(Colombia):
    pass


class COL(Colombia):
    pass
