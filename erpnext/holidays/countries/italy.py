#  python-holidays
#  ---------------
#  A fast, efficient Python library for generating country, province and state
#  specific sets of holidays on the fly. It aims to make determining whether a
#  specific date is a holiday as fast and flexible as possible.
#
#  Authors: dr-prodigy <dr.prodigy.github@gmail.com> (c) 2017-2023
#           ryanss <ryanssdev@icloud.com> (c) 2014-2017
#  Provinces completed by Henrik Sozzi <henrik_sozzi@hotmail.com>
#  Website: https://github.com/dr-prodigy/python-holidays
#  License: MIT (see LICENSE file)

from datetime import timedelta as td

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
    TUE,
    SUN,
)
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Italy(HolidayBase, ChristianHolidays, InternationalHolidays):
    country = "IT"
    # Reference: https://it.wikipedia.org/wiki/Province_d%27Italia
    # Please maintain in alphabetical order for easy updating in the future
    # The alphabetical order is except cities of provinces with multiple head
    # cities that directly follows the main province id like BT, Barletta,
    # Andria, Trani, for easily grouping them.
    # In that case if you use the 2 char id you'll take the first Santo
    # Patrono defined. If you want one specific you'll have to use
    # the full name of the city like "Andria" instead of "BT".
    subdivisions = (
        # Provinces.
        "AG",
        "AL",
        "AN",
        "AO",
        "AP",
        "AQ",
        "AR",
        "AT",
        "AV",
        "BA",
        "BG",
        "BI",
        "BL",
        "BN",
        "BO",
        "BR",
        "BS",
        "BT",
        "BZ",
        "CA",
        "CB",
        "CE",
        "CH",
        "CL",
        "CN",
        "CO",
        "CR",
        "CS",
        "CT",
        "CZ",
        "EN",
        "FC",
        "FE",
        "FG",
        "FI",
        "FM",
        "FR",
        "GE",
        "GO",
        "GR",
        "IM",
        "IS",
        "KR",
        "LC",
        "LE",
        "LI",
        "LO",
        "LT",
        "LU",
        "MB",
        "MC",
        "ME",
        "MI",
        "MN",
        "MO",
        "MS",
        "MT",
        "NA",
        "NO",
        "NU",
        "OR",
        "PA",
        "PC",
        "PD",
        "PE",
        "PG",
        "PI",
        "PN",
        "PO",
        "PR",
        "PT",
        "PU",
        "PV",
        "PZ",
        "RA",
        "RC",
        "RE",
        "RG",
        "RI",
        "RM",
        "RN",
        "RO",
        "SA",
        "SI",
        "SO",
        "SP",
        "SR",
        "SS",
        "SU",
        "SV",
        "TA",
        "TE",
        "TN",
        "TO",
        "TP",
        "TR",
        "TS",
        "TV",
        "UD",
        "VA",
        "VB",
        "VC",
        "VE",
        "VI",
        "VR",
        "VT",
        "VV",
        # Cities.
        "Andria",
        "Barletta",
        "Cesena",
        "Forli",
        "Pesaro",
        "Trani",
        "Urbino",
    )

    _deprecated_subdivisions = ("Forlì",)

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day("Capodanno")

        # Epiphany.
        self._add_epiphany_day("Epifania del Signore")

        # Easter Sunday.
        self._add_easter_sunday("Pasqua di Resurrezione")

        # Easter Monday.
        self._add_easter_monday("Lunedì dell'Angelo")

        if year >= 1946:
            # Liberation Day.
            self._add_holiday("Festa della Liberazione", APR, 25)

        # Labor Day.
        self._add_labor_day("Festa dei Lavoratori")

        if year >= 1948:
            # Republic Day.
            self._add_holiday("Festa della Repubblica", JUN, 2)

        # Assumption Of Mary Day.
        self._add_assumption_of_mary_day("Assunzione della Vergine")

        # All Saints' Day.
        self._add_all_saints_day("Tutti i Santi")

        # Immaculate Conception Day.
        self._add_immaculate_conception_day("Immacolata Concezione")

        # Christmas Day.
        self._add_christmas_day("Natale")

        self._add_christmas_day_two("Santo Stefano")

        if self.subdiv == "Forlì":
            self._add_subdiv_forli_holidays()

    # Provinces holidays.
    # https://it.wikipedia.org/wiki/Santi_patroni_cattolici_delle_citt%C3%A0_capoluogo_di_provincia_italiane
    # Please maintain in alphabetical order for easy updating in the future.

    def _add_subdiv_ag_holidays(self):
        self._add_holiday("San Gerlando", FEB, 25)

    def _add_subdiv_al_holidays(self):
        self._add_holiday("San Baudolino", NOV, 10)

    def _add_subdiv_an_holidays(self):
        self._add_holiday("San Ciriaco", MAY, 4)

    def _add_subdiv_ao_holidays(self):
        self._add_holiday("San Grato", SEP, 7)

    def _add_subdiv_ap_holidays(self):
        self._add_holiday("Sant'Emidio", AUG, 5)

    def _add_subdiv_aq_holidays(self):
        self._add_holiday("San Massimo D'Aveia", JUN, 10)

    def _add_subdiv_ar_holidays(self):
        self._add_holiday("San Donato D'Arezzo", AUG, 7)

    def _add_subdiv_at_holidays(self):
        self._add_holiday("San Secondo di Asti", self._get_nth_weekday_of_month(1, TUE, MAY))

    def _add_subdiv_av_holidays(self):
        self._add_holiday("San Modestino", FEB, 14)

    def _add_subdiv_ba_holidays(self):
        self._add_holiday("San Nicola", DEC, 6)

    def _add_subdiv_bg_holidays(self):
        self._add_holiday("Sant'Alessandro di Bergamo", AUG, 26)

    def _add_subdiv_bi_holidays(self):
        self._add_christmas_day_two("Santo Stefano")

    def _add_subdiv_bl_holidays(self):
        self._add_holiday("San Martino", NOV, 11)

    def _add_subdiv_bn_holidays(self):
        self._add_holiday("San Bartolomeo apostolo", AUG, 24)

    def _add_subdiv_bo_holidays(self):
        self._add_holiday("San Petronio", OCT, 4)

    def _add_subdiv_br_holidays(self):
        self._add_holiday(
            "San Teodoro d'Amasea e San Lorenzo da Brindisi",
            self._get_nth_weekday_of_month(1, SUN, SEP),
        )

    def _add_subdiv_bs_holidays(self):
        self._add_holiday("Santi Faustino e Giovita", FEB, 15)

    def _add_subdiv_bt_holidays(self):
        self._add_holiday("San Nicola Pellegrino", MAY, 3)
        self._add_holiday("San Riccardo di Andria", self._get_nth_weekday_of_month(3, SUN, SEP))
        self._add_holiday("San Ruggero", DEC, 30)

    def _add_subdiv_bz_holidays(self):
        self._add_whit_monday("Lunedì di Pentecoste")
        self._add_assumption_of_mary_day("Maria Santissima Assunta")

    def _add_subdiv_ca_holidays(self):
        self._add_holiday("San Saturnino di Cagliari", OCT, 30)

    def _add_subdiv_cb_holidays(self):
        self._add_saint_georges_day("San Giorgio")

    def _add_subdiv_ce_holidays(self):
        self._add_holiday("San Sebastiano", JAN, 20)

    def _add_subdiv_ch_holidays(self):
        self._add_holiday("San Giustino di Chieti", MAY, 11)

    def _add_subdiv_cl_holidays(self):
        self._add_holiday("San Michele Arcangelo", SEP, 29)

    def _add_subdiv_cn_holidays(self):
        self._add_holiday("San Michele Arcangelo", SEP, 29)

    def _add_subdiv_co_holidays(self):
        self._add_holiday("Sant'Abbondio", AUG, 31)

    def _add_subdiv_cr_holidays(self):
        self._add_holiday("Sant'Omobono", NOV, 13)

    def _add_subdiv_cs_holidays(self):
        self._add_holiday("Madonna del Pilerio", FEB, 12)

    def _add_subdiv_ct_holidays(self):
        self._add_holiday("Sant'Agata", FEB, 5)

    def _add_subdiv_cz_holidays(self):
        self._add_holiday("San Vitaliano", JUL, 16)

    def _add_subdiv_en_holidays(self):
        self._add_holiday("Madonna della Visitazione", JUL, 2)

    def _add_subdiv_fc_holidays(self):
        self._add_holiday("Madonna del Fuoco", FEB, 4)
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_fe_holidays(self):
        self._add_saint_georges_day("San Giorgio")

    def _add_subdiv_fg_holidays(self):
        self._add_holiday("Madonna dei Sette Veli", MAR, 22)

    def _add_subdiv_fi_holidays(self):
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_fm_holidays(self):
        aug_15 = self._add_assumption_of_mary_day("Maria Santissima Assunta")
        self._add_holiday("Maria Santissima Assunta", aug_15 + td(days=+1))

    def _add_subdiv_fr_holidays(self):
        self._add_holiday("San Silverio", JUN, 20)

    def _add_subdiv_ge_holidays(self):
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_go_holidays(self):
        self._add_holiday("Santi Ilario e Taziano", MAR, 16)

    def _add_subdiv_gr_holidays(self):
        self._add_holiday("San Lorenzo", AUG, 10)

    def _add_subdiv_im_holidays(self):
        self._add_holiday("San Leonardo da Porto Maurizio", NOV, 26)

    def _add_subdiv_is_holidays(self):
        self._add_holiday("San Pietro Celestino", MAY, 19)

    def _add_subdiv_kr_holidays(self):
        self._add_holiday("San Dionigi", OCT, 9)

    def _add_subdiv_lc_holidays(self):
        self._add_holiday("San Nicola", DEC, 6)

    def _add_subdiv_le_holidays(self):
        self._add_holiday("Sant'Oronzo", AUG, 26)

    def _add_subdiv_li_holidays(self):
        self._add_holiday("Santa Giulia", MAY, 22)

    def _add_subdiv_lo_holidays(self):
        self._add_holiday("San Bassiano", JAN, 19)

    def _add_subdiv_lt_holidays(self):
        self._add_holiday("San Marco evangelista", APR, 25)

    def _add_subdiv_lu_holidays(self):
        self._add_holiday("San Paolino di Lucca", JUL, 12)

    def _add_subdiv_mb_holidays(self):
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_mc_holidays(self):
        self._add_holiday("San Giuliano l'ospitaliere", AUG, 31)

    def _add_subdiv_me_holidays(self):
        self._add_holiday("Madonna della Lettera", JUN, 3)

    def _add_subdiv_mi_holidays(self):
        self._add_holiday("Sant'Ambrogio", DEC, 7)

    def _add_subdiv_mn_holidays(self):
        self._add_holiday("Sant'Anselmo da Baggio", MAR, 18)

    def _add_subdiv_mo_holidays(self):
        self._add_holiday("San Geminiano", JAN, 31)

    def _add_subdiv_ms_holidays(self):
        self._add_holiday("San Francesco d'Assisi", OCT, 4)

    def _add_subdiv_mt_holidays(self):
        self._add_holiday("Madonna della Bruna", JUL, 2)

    def _add_subdiv_na_holidays(self):
        self._add_holiday("San Gennaro", SEP, 19)

    def _add_subdiv_no_holidays(self):
        self._add_holiday("San Gaudenzio", JAN, 22)

    def _add_subdiv_nu_holidays(self):
        self._add_holiday("Nostra Signora della Neve", AUG, 5)

    def _add_subdiv_or_holidays(self):
        self._add_holiday("Sant'Archelao", FEB, 13)

    def _add_subdiv_pa_holidays(self):
        self._add_holiday("San Giovanni", JUL, 15)

    def _add_subdiv_pc_holidays(self):
        self._add_holiday("Sant'Antonino di Piacenza", JUL, 4)

    def _add_subdiv_pd_holidays(self):
        self._add_holiday("Sant'Antonio di Padova", JUN, 13)

    def _add_subdiv_pe_holidays(self):
        self._add_holiday("San Cetteo", OCT, 10)

    def _add_subdiv_pg_holidays(self):
        self._add_holiday("Sant'Ercolano e San Lorenzo", JAN, 29)

    def _add_subdiv_pi_holidays(self):
        self._add_holiday("San Ranieri", JUN, 17)

    def _add_subdiv_pn_holidays(self):
        self._add_holiday("San Marco Evangelista", APR, 25)
        self._add_nativity_of_mary_day("Madonna delle Grazie")

    def _add_subdiv_po_holidays(self):
        self._add_christmas_day_two("Santo Stefano")

    def _add_subdiv_pr_holidays(self):
        self._add_holiday("Sant'Ilario di Poitiers", JAN, 13)

    def _add_subdiv_pt_holidays(self):
        self._add_saint_james_day("San Jacopo")

    def _add_subdiv_pu_holidays(self):
        self._add_holiday("San Crescentino", JUN, 1)
        self._add_holiday("San Terenzio di Pesaro", SEP, 24)

    def _add_subdiv_pv_holidays(self):
        self._add_holiday("San Siro", DEC, 9)

    def _add_subdiv_pz_holidays(self):
        self._add_holiday("San Gerardo di Potenza", MAY, 30)

    def _add_subdiv_ra_holidays(self):
        self._add_holiday("Sant'Apollinare", JUL, 23)

    def _add_subdiv_rc_holidays(self):
        self._add_saint_georges_day("San Giorgio")

    def _add_subdiv_re_holidays(self):
        self._add_holiday("San Prospero Vescovo", NOV, 24)

    def _add_subdiv_rg_holidays(self):
        self._add_saint_georges_day("San Giorgio")

    def _add_subdiv_ri_holidays(self):
        self._add_holiday("Santa Barbara", DEC, 4)

    def _add_subdiv_rm_holidays(self):
        self._add_saints_peter_and_paul_day("Santi Pietro e Paolo")

    def _add_subdiv_rn_holidays(self):
        self._add_holiday("San Gaudenzio", OCT, 14)

    def _add_subdiv_ro_holidays(self):
        self._add_holiday("San Bellino", NOV, 26)

    def _add_subdiv_sa_holidays(self):
        self._add_holiday("San Matteo Evangelista", SEP, 21)

    def _add_subdiv_si_holidays(self):
        self._add_holiday("Sant'Ansano", DEC, 1)

    def _add_subdiv_so_holidays(self):
        self._add_holiday("San Gervasio e San Protasio", JUN, 19)

    def _add_subdiv_sp_holidays(self):
        self._add_saint_josephs_day("San Giuseppe")

    def _add_subdiv_sr_holidays(self):
        self._add_holiday("Santa Lucia", DEC, 13)

    def _add_subdiv_ss_holidays(self):
        self._add_holiday("San Nicola", DEC, 6)

    def _add_subdiv_su_holidays(self):
        self._add_holiday(
            "San Ponziano", self._get_nth_weekday_of_month(2, SUN, MAY) + td(days=+4)
        )

    def _add_subdiv_sv_holidays(self):
        self._add_holiday("Nostra Signora della Misericordia", MAR, 18)

    def _add_subdiv_ta_holidays(self):
        self._add_holiday("San Cataldo", MAY, 10)

    def _add_subdiv_te_holidays(self):
        self._add_holiday("San Berardo da Pagliara", DEC, 19)

    def _add_subdiv_tn_holidays(self):
        self._add_holiday("San Vigilio", JUN, 26)

    def _add_subdiv_to_holidays(self):
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_tp_holidays(self):
        self._add_holiday("Sant'Alberto degli Abati", AUG, 7)

    def _add_subdiv_tr_holidays(self):
        self._add_holiday("San Valentino", FEB, 14)

    def _add_subdiv_ts_holidays(self):
        self._add_holiday("San Giusto", NOV, 3)

    def _add_subdiv_tv_holidays(self):
        self._add_holiday("San Liberale", APR, 27)

    def _add_subdiv_ud_holidays(self):
        self._add_holiday("Santi Ermacora e Fortunato", JUL, 12)

    def _add_subdiv_va_holidays(self):
        self._add_holiday("San Vittore il Moro", MAY, 8)

    def _add_subdiv_vb_holidays(self):
        self._add_holiday("San Vittore il Moro", MAY, 8)

    def _add_subdiv_vc_holidays(self):
        self._add_holiday("Sant'Eusebio di Vercelli", AUG, 1)

    def _add_subdiv_ve_holidays(self):
        self._add_holiday("San Marco Evangelista", APR, 25)

    def _add_subdiv_vi_holidays(self):
        self._add_holiday("San Marco", APR, 25)

    def _add_subdiv_vr_holidays(self):
        self._add_holiday("San Zeno", MAY, 21)

    def _add_subdiv_vt_holidays(self):
        self._add_holiday("Santa Rosa da Viterbo", SEP, 4)

    def _add_subdiv_vv_holidays(self):
        self._add_holiday("San Leoluca", MAR, 1)

    def _add_subdiv_andria_holidays(self):
        self._add_holiday("San Riccardo di Andria", self._get_nth_weekday_of_month(3, SUN, SEP))

    def _add_subdiv_barletta_holidays(self):
        self._add_holiday("San Ruggero", DEC, 30)

    def _add_subdiv_cesena_holidays(self):
        self._add_saint_johns_day("San Giovanni Battista")

    def _add_subdiv_forli_holidays(self):
        self._add_holiday("Madonna del Fuoco", FEB, 4)

    def _add_subdiv_pesaro_holidays(self):
        self._add_holiday("San Terenzio di Pesaro", SEP, 24)

    def _add_subdiv_trani_holidays(self):
        self._add_holiday("San Nicola Pellegrino", MAY, 3)

    def _add_subdiv_urbino_holidays(self):
        self._add_holiday("San Crescentino", JUN, 1)


class IT(Italy):
    pass


class ITA(Italy):
    pass
