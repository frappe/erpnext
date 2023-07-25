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
from typing import Optional

from holidays.calendars.gregorian import FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Spain(HolidayBase, ChristianHolidays, IslamicHolidays, InternationalHolidays):
    """
    References:
     - https://administracion.gob.es/pag_Home/atencionCiudadana/calendarios.html
    """

    country = "ES"
    subdivisions = (
        "AN",
        "AR",
        "AS",
        "CB",
        "CE",
        "CL",
        "CM",
        "CN",
        "CT",
        "EX",
        "GA",
        "IB",
        "MC",
        "MD",
        "ML",
        "NC",
        "PV",
        "RI",
        "VC",
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_holiday(self, *args) -> Optional[date]:
        name, dt = self._parse_holiday(*args)
        if dt.year != self._year:
            return None
        if self.observed and self._is_sunday(dt):
            dt += td(days=+1)
            name = self.tr("%s (Trasladado)") % self.tr(name)
        self[dt] = self.tr(name)
        return dt

    def _populate(self, year):
        super()._populate(year)

        if year != 2023:
            self._add_new_years_day("Año nuevo")

        self._add_epiphany_day("Epifanía del Señor")

        if year >= 2023:
            self._add_holy_thursday("Jueves Santo")

        self._add_good_friday("Viernes Santo")

        if year != 2022:
            self._add_labor_day("Día del Trabajador")

        self._add_assumption_of_mary_day("Asunción de la Virgen")

        self._add_holiday("Día de la Hispanidad", OCT, 12)

        self._add_all_saints_day("Todos los Santos")

        self._add_holiday("Día de la Constitución Española", DEC, 6)

        self._add_immaculate_conception_day("La Inmaculada Concepción")

        if year != 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_an_holidays(self):
        if self._year == 2023:
            self._add_new_years_day("Año nuevo")
        self._add_holiday("Día de Andalucia", FEB, 28)
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
            self._add_christmas_day("Navidad")

    def _add_subdiv_ar_holidays(self):
        if self._year == 2023:
            self._add_new_years_day("Año nuevo")
        if self._year <= 2014:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_saint_georges_day("Día de San Jorge")
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
            self._add_christmas_day("Navidad")

    def _add_subdiv_as_holidays(self):
        if self._year == 2023:
            self._add_new_years_day("Año nuevo")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de Asturias", SEP, 8)
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
            self._add_christmas_day("Navidad")

    def _add_subdiv_cb_holidays(self):
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de las Instituciones de Cantabria", JUL, 28)
        self._add_holiday("Día de la Bien Aparecida", SEP, 15)
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_ce_holidays(self):
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Nuestra Señora de África", AUG, 5)
        self._add_holiday("Día de la Ciudad Autónoma de Ceuta", SEP, 2)
        if self._year == 2022:
            self._add_eid_al_adha_day("Eid al-Adha")
        elif self._year == 2023:
            self._add_eid_al_adha_day_two("Eid al-Adha")

    def _add_subdiv_cl_holidays(self):
        if self._year == 2023:
            self._add_new_years_day("Año nuevo")
            self._add_saint_james_day("Día de Santiago Apóstol")
        if self._year <= 2014:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de Castilla y Leon", APR, 23)
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
            self._add_christmas_day("Navidad")

    def _add_subdiv_cm_holidays(self):
        if self._year <= 2015 or 2020 <= self._year <= 2021:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        if self._year <= 2021:
            self._add_easter_monday("Lunes de Pascua")
        if self._year >= 2022:
            self._add_corpus_christi_day("Corpus Christi")
        self._add_holiday("Día de Castilla La Mancha", MAY, 31)
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_cn_holidays(self):
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de Canarias", MAY, 30)
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_ct_holidays(self):
        self._add_easter_monday("Lunes de Pascua")
        if self._year == 2022:
            self._add_holiday("Día de la Pascua Granada", JUN, 6)
        self._add_saint_johns_day("San Juan")
        self._add_holiday("Día Nacional de Catalunya", SEP, 11)
        if self._year == 2022:
            self._add_christmas_day("Navidad")
        self._add_christmas_day_two("San Esteban")

    def _add_subdiv_ex_holidays(self):
        if self._year <= 2014:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de Extremadura", SEP, 8)
        if self._year == 2023:
            self._add_carnival_tuesday("Carnaval")
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
            self._add_christmas_day("Navidad")

    def _add_subdiv_ga_holidays(self):
        if self._year <= 2014 or 2018 <= self._year <= 2021:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        if self._year >= 2022:
            self._add_holiday("Día de las letras Gallegas", MAY, 17)
        if self._year != 2023:
            self._add_saint_johns_day("San Juan")
        self._add_holiday("Día Nacional de Galicia", JUL, 25)

    def _add_subdiv_ib_holidays(self):
        self._add_holiday("Día de las Islas Baleares", MAR, 1)
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_easter_monday("Lunes de Pascua")
        if self._year == 2022:
            self._add_christmas_day("Navidad")
        if self._year <= 2020:
            self._add_christmas_day_two("San Esteban")

    def _add_subdiv_mc_holidays(self):
        if self._year == 2023:
            self._add_new_years_day("Año nuevo")
        if self._year <= 2021 and self._year != 2017:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        if self._year == 2022:
            self._add_labor_day("Día del Trabajador")
        self._add_holiday("Día de la Región de Murcia", JUN, 9)
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_md_holidays(self):
        if self._year <= 2015 or self._year == 2023:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Día de Comunidad de Madrid", MAY, 2)
        if self._year == 2022:
            self._add_saint_james_day("Día de Santiago Apóstol")
            self._add_christmas_day("Navidad")

    def _add_subdiv_ml_holidays(self):
        if self._year <= 2016:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_holiday("Vírgen de la victoria", SEP, 8)
        self._add_holiday("Día de Melilla", SEP, 17)
        if self._year == 2022:
            self._add_eid_al_fitr_day_two("Eid al-Fitr")
            self._add_eid_al_adha_day_three("Eid al-Adha")
            self._add_christmas_day("Navidad")
        elif self._year == 2023:
            self._add_eid_al_fitr_day("Eid al-Fitr")
            self._add_eid_al_adha_day_two("Eid al-Adha")

    def _add_subdiv_nc_holidays(self):
        if self._year <= 2015 or 2018 <= self._year <= 2021:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_easter_monday("Lunes de Pascua")
        if self._year >= 2022:
            self._add_saint_james_day("Día de Santiago Apóstol")
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_pv_holidays(self):
        if self._year <= 2021:
            self._add_saint_josephs_day("San José")
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_easter_monday("Lunes de Pascua")
        if self._year >= 2022:
            self._add_saint_james_day("Día de Santiago Apóstol")
        if self._year <= 2022:
            self._add_holiday("Día de Elcano", SEP, 6)
        if 2011 <= self._year <= 2013:
            self._add_holiday("Día del País Vasco", OCT, 25)

    def _add_subdiv_ri_holidays(self):
        if self._year <= 2022:
            self._add_holy_thursday("Jueves Santo")
        if self._year >= 2022:
            self._add_easter_monday("Lunes de Pascua")
        self._add_holiday("Día de La Rioja", JUN, 9)
        if self._year == 2022:
            self._add_christmas_day("Navidad")

    def _add_subdiv_vc_holidays(self):
        if self._year <= 2022 and self._year != 2017:
            self._add_saint_josephs_day("San José")
        if self._year == 2022:
            self._add_holy_thursday("Jueves Santo")
        self._add_easter_monday("Lunes de Pascua")
        self._add_saint_johns_day("San Juan")
        if self._year <= 2021:
            self._add_holiday("Día de la Comunidad Valenciana", OCT, 9)


class ES(Spain):
    pass


class ESP(Spain):
    pass
