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
from datetime import date

from holidays.calendars.gregorian import (
    JAN,
    FEB,
    MAR,
    APR,
    MAY,
    JUN,
    JUL,
    AUG,
    SEP,
    OCT,
    NOV,
    DEC,
    FRI,
    SUN,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Brazil(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    References:
    - https://pt.wikipedia.org/wiki/Feriados_no_Brasil
    - Decreto n. 155-B, de 14.01.1890:
        https://www2.camara.leg.br/legin/fed/decret/1824-1899/decreto-155-b-14-janeiro-1890-517534-publicacaooriginal-1-pe.html
    - Decreto n. 19.488, de 15.12.1930:
        https://www2.camara.leg.br/legin/fed/decret/1930-1939/decreto-19488-15-dezembro-1930-508040-republicacao-85201-pe.html
    """

    country = "BR"
    subdivisions = (
        "AC",  # Acre
        "AL",  # Alagoas
        "AM",  # Amazonas
        "AP",  # Amapá
        "BA",  # Bahia
        "CE",  # Ceará
        "DF",  # Distrito Federal
        "ES",  # Espírito Santo
        "GO",  # Goiás
        "MA",  # Maranhão
        "MG",  # Minas Gerais
        "MS",  # Mato Grosso do Sul
        "MT",  # Mato Grosso
        "PA",  # Pará
        "PB",  # Paraíba
        "PE",  # Pernambuco
        "PI",  # Piauí
        "PR",  # Paraná
        "RJ",  # Rio de Janeiro
        "RN",  # Rio Grande do Norte
        "RO",  # Rondônia
        "RR",  # Roraima
        "RS",  # Rio Grande do Sul
        "SC",  # Santa Catarina
        "SE",  # Sergipe
        "SP",  # São Paulo
        "TO",  # Tocantins
    )

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # Decreto n. 155-B, de 14.01.1890
        if year <= 1889:
            return None
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("Confraternização Universal")

        if 1892 <= year <= 1930:
            # Republic Constitution Day.
            self._add_holiday("Constituição da Republica", FEB, 24)

        # Good Friday.
        self._add_good_friday("Sexta-feira Santa")

        if year not in {1931, 1932}:
            # Tiradentes' Day.
            self._add_holiday("Tiradentes", APR, 21)

        if year >= 1925:
            # Labor Day.
            self._add_labor_day("Dia do Trabalhador")

        if year <= 1930:
            # Discovery of Brazil.
            self._add_holiday("Descobrimento do Brasil", MAY, 3)

            # Abolition of slavery in Brazil.
            self._add_holiday("Abolição da escravidão no Brasil", MAY, 13)

            # Freedom and Independence of American Peoples.
            self._add_holiday("Liberdade e Independência dos Povos Americanos", JUL, 14)

        # Independence Day.
        self._add_holiday("Independência do Brasil", SEP, 7)

        if year <= 1930 or year >= 1980:
            # Our Lady of Aparecida.
            self._add_holiday("Nossa Senhora Aparecida", OCT, 12)

        # All Souls' Day.
        self._add_all_souls_day("Finados")

        # Republic Proclamation Day.
        self._add_holiday("Proclamação da República", NOV, 15)

        if year >= 1922:
            # Christmas Day.
            self._add_christmas_day("Natal")

        # Optional holidays

        # Carnival.
        self._add_carnival_monday("Carnaval")
        self._add_carnival_tuesday("Carnaval")

        # Ash Wednesday.
        self._add_ash_wednesday("Início da Quaresma")

        # Corpus Christi.
        self._add_corpus_christi_day("Corpus Christi")

        # Public Servant's Day.
        self._add_holiday("Dia do Servidor Público", OCT, 28)

        # Christmas Eve.
        self._add_christmas_eve("Véspera de Natal")

        # New Year's Eve.
        self._add_new_years_eve("Véspera de Ano-Novo")

    def _add_subdiv_holidays(self):
        # Lei n. 9.093, de 12.09.1995
        if self._year >= 1996:
            super()._add_subdiv_holidays()

    def _add_subdiv_ac_holidays(self):
        def get_movable_acre(*args) -> date:
            dt = date(self._year, *args)
            if self._year >= 2009 and (
                self._is_tuesday(dt) or self._is_wednesday(dt) or self._is_thursday(dt)
            ):
                dt = self._get_nth_weekday_from(1, FRI, dt)
            return dt

        if self._year >= 2005:
            # Evangelical Day.
            self._add_holiday("Dia do Evangélico", get_movable_acre(JAN, 23))

        if self._year >= 2002:
            # International Women's Day.
            self._add_holiday("Dia Internacional da Mulher", get_movable_acre(MAR, 8))

        # Founding of Acre.
        self._add_holiday("Aniversário do Acre", JUN, 15)

        if self._year >= 2004:
            # Amazonia Day.
            self._add_holiday("Dia da Amazônia", get_movable_acre(SEP, 5))

        # Signing of the Petropolis Treaty.
        self._add_holiday("Assinatura do Tratado de Petrópolis", get_movable_acre(NOV, 17))

    def _add_subdiv_al_holidays(self):
        # Saint John's Day.
        self._add_saint_johns_day("São João")

        # Saint Peter's Day.
        self._add_saints_peter_and_paul_day("São Pedro")

        # Political Emancipation of Alagoas.
        self._add_holiday("Emancipação Política de Alagoas", SEP, 16)

        # Black Awareness Day.
        self._add_holiday("Consciência Negra", NOV, 20)

        if self._year >= 2013:
            self._add_holiday("Dia do Evangélico", NOV, 30)

    def _add_subdiv_am_holidays(self):
        # Elevation of Amazonas to province.
        self._add_holiday("Elevação do Amazonas à categoria de província", SEP, 5)

        if self._year >= 2010:
            self._add_holiday("Consciência Negra", NOV, 20)

    def _add_subdiv_ap_holidays(self):
        if self._year >= 2003:
            # Saint Joseph's Day.
            self._add_saint_josephs_day("São José")

        if self._year >= 2012:
            # Saint James' Day.
            self._add_saint_james_day("São Tiago")

        # Creation of the Federal Territory.
        self._add_holiday("Criação do Território Federal", SEP, 13)

        if self._year >= 2008:
            self._add_holiday("Consciência Negra", NOV, 20)

    def _add_subdiv_ba_holidays(self):
        # Bahia Independence Day.
        self._add_holiday("Independência da Bahia", JUL, 2)

    def _add_subdiv_ce_holidays(self):
        self._add_saint_josephs_day("São José")

        # Abolition of slavery in Ceará.
        self._add_holiday("Abolição da escravidão no Ceará", MAR, 25)

        if self._year >= 2004:
            # Our Lady of Assumption.
            self._add_assumption_of_mary_day("Nossa Senhora da Assunção")

    def _add_subdiv_df_holidays(self):
        # Founding of Brasilia.
        self._add_holiday("Fundação de Brasília", APR, 21)

        self._add_holiday("Dia do Evangélico", NOV, 30)

    def _add_subdiv_es_holidays(self):
        if self._year >= 2020:
            # Our Lady of Penha.
            self._add_holiday("Nossa Senhora da Penha", self._easter_sunday + td(days=+8))

    def _add_subdiv_go_holidays(self):
        # Foundation of Goiás city.
        self._add_holiday("Fundação da cidade de Goiás", JUL, 26)

        # Foundation of Goiânia.
        self._add_holiday("Pedra fundamental de Goiânia", OCT, 24)

    def _add_subdiv_ma_holidays(self):
        # Maranhão joining to independence of Brazil.
        self._add_holiday("Adesão do Maranhão à independência do Brasil", JUL, 28)

    def _add_subdiv_mg_holidays(self):
        # Tiradentes' Execution.
        self._add_holiday("Execução de Tiradentes", APR, 21)

    def _add_subdiv_ms_holidays(self):
        # State Creation Day.
        self._add_holiday("Criação do Estado", OCT, 11)

    def _add_subdiv_mt_holidays(self):
        if self._year >= 2003:
            self._add_holiday("Consciência Negra", NOV, 20)

    def _add_subdiv_pa_holidays(self):
        # Grão-Pará joining to independence of Brazil.
        self._add_holiday("Adesão do Grão-Pará à independência do Brasil", AUG, 15)

    def _add_subdiv_pb_holidays(self):
        # State Founding Day.
        self._add_holiday("Fundação do Estado", AUG, 5)

    def _add_subdiv_pe_holidays(self):
        if self._year >= 2008:
            self._add_holiday(
                # Pernambuco Revolution.
                "Revolução Pernambucana",
                self._get_nth_weekday_of_month(1, SUN, MAR),
            )

    def _add_subdiv_pi_holidays(self):
        # Piauí Day.
        self._add_holiday("Dia do Piauí", OCT, 19)

    def _add_subdiv_pr_holidays(self):
        # Emancipation of Paraná.
        self._add_holiday("Emancipação do Paraná", DEC, 19)

    def _add_subdiv_rj_holidays(self):
        if self._year >= 2008:
            # Saint George's Day.
            self._add_saint_georges_day("São Jorge")

        if self._year >= 2002:
            self._add_holiday("Consciência Negra", NOV, 20)

    def _add_subdiv_rn_holidays(self):
        if self._year >= 2000:
            # Rio Grande do Norte Day.
            self._add_holiday("Dia do Rio Grande do Norte", AUG, 7)

        if self._year >= 2007:
            # Uruaçú and Cunhaú Martyrs Day.
            self._add_holiday("Mártires de Cunhaú e Uruaçuu", OCT, 3)

    def _add_subdiv_ro_holidays(self):
        self._add_holiday("Criação do Estado", JAN, 4)

        if self._year >= 2002:
            self._add_holiday("Dia do Evangélico", JUN, 18)

    def _add_subdiv_rr_holidays(self):
        self._add_holiday("Criação do Estado", OCT, 5)

    def _add_subdiv_rs_holidays(self):
        # Gaucho Day.
        self._add_holiday("Dia do Gaúcho", SEP, 20)

    def _add_subdiv_sc_holidays(self):
        if self._year >= 2004:
            dt = date(self._year, AUG, 11)
            if self._year >= 2005:
                dt = self._get_nth_weekday_from(1, SUN, dt)
            # Santa Catarina State Day.
            self._add_holiday("Dia do Estado de Santa Catarina", dt)

        dt = date(self._year, NOV, 25)
        if 1999 <= self._year != 2004:
            dt = self._get_nth_weekday_from(1, SUN, dt)
        # Saint Catherine of Alexandria Day.
        self._add_holiday("Dia de Santa Catarina de Alexandria", dt)

    def _add_subdiv_se_holidays(self):
        # Sergipe Political Emancipation Day.
        self._add_holiday("Emancipação política de Sergipe", JUL, 8)

    def _add_subdiv_sp_holidays(self):
        if self._year >= 1997:
            # Constitutionalist Revolution.
            self._add_holiday("Revolução Constitucionalista", JUL, 9)

    def _add_subdiv_to_holidays(self):
        if self._year >= 1998:
            # Autonomy Day.
            self._add_holiday("Dia da Autonomia", MAR, 18)

        # Our Lady of Nativity.
        self._add_nativity_of_mary_day("Nossa Senhora da Natividade")

        self._add_holiday("Criação do Estado", OCT, 5)


class BR(Brazil):
    pass


class BRA(Brazil):
    pass
