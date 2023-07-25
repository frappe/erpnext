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

from datetime import timedelta as td
from gettext import gettext as tr

from holidays.calendars.gregorian import APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Portugal(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    A subclass of :py:class:`HolidayBase` representing public holidays
    in Portugal.

    References:

    - Based on:
        https://en.wikipedia.org/wiki/Public_holidays_in_Portugal

    National Level:
    - [Labour Day]
        https://www.e-konomista.pt/dia-do-trabalhador/
    - [Portugal Day]
        Decreto 17.171
    - [Restoration of Independence Day]
        Gazeta de Lisboa, 8 de Dezembro de 1823 (n.º 290), pp. 1789 e 1790

    Regional Level:
    - [Azores]
        https://files.dre.pt/1s/1980/08/19200/23052305.pdf
    - [Madeira]
        https://files.dre.pt/1s/1979/11/25900/28782878.pdf
        https://files.dre.pt/1s/1989/02/02800/04360436.pdf
        https://files.dre.pt/1s/2002/11/258a00/71837183.pdf

    """

    country = "PT"
    default_language = "pt_PT"

    # https://en.wikipedia.org/wiki/ISO_3166-2:PT
    # `Ext` represents the national holidays most people have off
    subdivisions = (
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "20",
        "30",
        "Ext",
    )
    supported_languages = ("en_US", "pt_PT")

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        self._add_new_years_day(tr("Ano Novo"))

        # Carnival is no longer a holiday, but some companies let workers off.
        # TODO: recollect the years in which it was a public holiday
        # self[e + td(days=-47)] = "Carnaval"

        # Good Friday.
        self._add_good_friday(tr("Sexta-feira Santa"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Páscoa"))

        # Revoked holidays in 2013–2015.
        if year <= 2012 or year >= 2016:
            self._add_corpus_christi_day(tr("Corpo de Deus"))
            if year >= 1910:
                self._add_holiday(tr("Implantação da República"), OCT, 5)
            self._add_all_saints_day(tr("Dia de Todos os Santos"))
            if year >= 1823:
                self._add_holiday(tr("Restauração da Independência"), DEC, 1)

        if year >= 1974:
            self._add_holiday(tr("Dia da Liberdade"), APR, 25)
            self._add_labor_day(tr("Dia do Trabalhador"))
        if year >= 1911:
            if 1933 <= year <= 1973:
                self._add_holiday(tr("Dia de Camões, de Portugal e da Raça"), JUN, 10)
            elif year >= 1978:
                self._add_holiday(
                    tr("Dia de Portugal, de Camões e das Comunidades Portuguesas"), JUN, 10
                )
            else:
                self._add_holiday(tr("Dia de Portugal"), JUN, 10)

        self._add_assumption_of_mary_day(tr("Assunção de Nossa Senhora"))
        self._add_immaculate_conception_day(tr("Imaculada Conceição"))
        self._add_christmas_day(tr("Dia de Natal"))

    def _add_subdiv_holidays(self):
        if self._year >= 1911:
            super()._add_subdiv_holidays()

    def _add_subdiv_ext_holidays(self):
        """
        Adds extended days that most people have as a bonus from their
        companies:

        - Carnival
        - the day before and after xmas
        - the day before the new year
        - Lisbon's city holiday
        """

        # TODO: add bridging days:
        # - get Holidays that occur on Tuesday  and add Monday (-1 day)
        # - get Holidays that occur on Thursday and add Friday (+1 day)

        self._add_carnival_monday(tr("Carnaval"))
        self._add_christmas_eve(tr("Véspera de Natal"))
        self._add_christmas_day_two(tr("26 de Dezembro"))
        self._add_new_years_eve(tr("Véspera de Ano Novo"))
        self._add_holiday(tr("Dia de Santo António"), JUN, 13)

    def _add_subdiv_01_holidays(self):
        self._add_holiday(tr("Dia de Santa Joana"), MAY, 12)

    def _add_subdiv_02_holidays(self):
        self._add_ascension_thursday(tr("Quinta-feira da Ascensão"))

    def _add_subdiv_03_holidays(self):
        self._add_holiday(tr("Dia de São João"), JUN, 24)

    def _add_subdiv_04_holidays(self):
        self._add_holiday(tr("Dia de Nossa Senhora das Graças"), AUG, 22)

    def _add_subdiv_05_holidays(self):
        self._add_holiday(
            tr("Dia de Nossa Senhora de Mércoles"), self._easter_sunday + td(days=+16)
        )

    def _add_subdiv_06_holidays(self):
        self._add_holiday(tr("Dia de Santa Isabel"), JUL, 4)

    def _add_subdiv_07_holidays(self):
        self._add_holiday(tr("Dia de São Pedro"), JUN, 29)

    def _add_subdiv_08_holidays(self):
        self._add_holiday(tr("Dia do Município de Faro"), SEP, 7)

    def _add_subdiv_09_holidays(self):
        self._add_holiday(tr("Dia do Município da Guarda"), NOV, 27)

    def _add_subdiv_10_holidays(self):
        self._add_holiday(tr("Dia do Município de Leiria"), MAY, 22)

    def _add_subdiv_11_holidays(self):
        self._add_holiday(tr("Dia de Santo António"), JUN, 13)

    def _add_subdiv_12_holidays(self):
        self._add_holiday(tr("Dia do Município de Portalegre"), MAY, 23)

    def _add_subdiv_13_holidays(self):
        self._add_holiday(tr("Dia de São João"), JUN, 24)

    def _add_subdiv_14_holidays(self):
        self._add_saint_josephs_day(tr("Dia de São José"))

    def _add_subdiv_15_holidays(self):
        self._add_holiday(tr("Dia de Bocage"), SEP, 15)

    def _add_subdiv_16_holidays(self):
        self._add_holiday(tr("Dia de Nossa Senhora da Agonia"), AUG, 20)

    def _add_subdiv_17_holidays(self):
        self._add_holiday(tr("Dia de Santo António"), JUN, 13)

    def _add_subdiv_18_holidays(self):
        self._add_holiday(tr("Dia de São Mateus"), SEP, 21)

    def _add_subdiv_20_holidays(self):
        if self._year >= 1981:
            self._add_holiday(
                tr("Dia da Região Autónoma dos Açores"), self._easter_sunday + td(days=+50)
            )

    def _add_subdiv_30_holidays(self):
        if 1979 <= self._year <= 1988:
            self._add_holiday(tr("Dia da Região Autónoma da Madeira"), JUL, 1)
        elif self._year >= 1989:
            self._add_holiday(
                tr("Dia da Região Autónoma da Madeira e das Comunidades Madeirenses"), JUL, 1
            )

        if self._year >= 2002:
            self._add_holiday(tr("Primeira Oitava"), DEC, 26)


class PT(Portugal):
    pass


class PRT(Portugal):
    pass
