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

from holidays.calendars.gregorian import MAR, APR, MAY, JUN, JUL, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class France(HolidayBase, ChristianHolidays, InternationalHolidays):
    """Official French holidays.

    Some provinces have specific holidays, only those are included in the
    PROVINCES, because these provinces have different administrative status,
    which makes it difficult to enumerate.

    For religious holidays usually happening on Sundays (Easter, Pentecost),
    only the following Monday is considered a holiday.

    Primary sources:
        https://fr.wikipedia.org/wiki/Fêtes_et_jours_fériés_en_France
        https://www.service-public.fr/particuliers/vosdroits/F2405
    """

    country = "FR"
    default_language = "fr"
    supported_languages = ("en_US", "fr", "uk")
    subdivisions = (
        "BL",  # Saint Barthelemy.
        "GES",  # Alsace, Champagne-Ardenne, Lorraine(Moselle).
        "GP",  # Guadeloupe.
        "GY",  # Guyane.
        "MF",  # Saint Martin.
        "MQ",  # Martinique.
        "NC",  # Nouvelle-Calédonie,
        "PF",  # Polynésie Française.
        "RE",  # Reunion.
        "WF",  # Wallis-et-Futuna.
        "YT",  # Mayotte.
    )

    _deprecated_subdivisions = (
        "Alsace-Moselle",
        "Guadeloupe",
        "Guyane",
        "La Réunion",
        "Martinique",
        "Mayotte",
        "Métropole",
        "Nouvelle-Calédonie",
        "Polynésie Française",
        "Saint-Barthélémy",
        "Saint-Martin",
        "Wallis-et-Futuna",
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # Civil holidays.
        if year >= 1811:
            # New Year's Day.
            self._add_new_years_day(tr("Jour de l'an"))

        if year >= 1919:
            self._add_labor_day(
                # Labor Day.
                tr("Fête du Travail")
                if year >= 1948
                # Labor and Social Concord Day.
                else tr("Fête du Travail et de la Concorde sociale")
            )

        if 1953 <= year <= 1959 or year >= 1982:
            # Victory Day.
            self._add_holiday(tr("Fête de la Victoire"), MAY, 8)

        if year >= 1880:
            # National Day.
            self._add_holiday(tr("Fête nationale"), JUL, 14)

        if year >= 1918:
            # Armistice Day.
            self._add_holiday(tr("Armistice"), NOV, 11)

        # Religious holidays.

        if year >= 1886:
            # Easter Monday.
            self._add_easter_monday(tr("Lundi de Pâques"))

            if year not in {2005, 2006, 2007}:
                # Whit Monday.
                self._add_whit_monday(tr("Lundi de Pentecôte"))

        if year >= 1802:
            # Ascension Day.
            self._add_ascension_thursday(tr("Ascension"))
            # Assumption Day.
            self._add_assumption_of_mary_day(tr("Assomption"))
            # All Saints' Day.
            self._add_all_saints_day(tr("Toussaint"))
            # Christmas Day.
            self._add_christmas_day(tr("Noël"))

        if self.subdiv == "Alsace-Moselle":
            self._add_subdiv_ges_holidays()
        elif self.subdiv == "Guadeloupe":
            self._add_subdiv_gp_holidays()
        elif self.subdiv == "Guyane":
            self._add_subdiv_gy_holidays()
        elif self.subdiv == "La Réunion":
            self._add_subdiv_re_holidays()
        elif self.subdiv == "Martinique":
            self._add_subdiv_mq_holidays()
        elif self.subdiv == "Mayotte":
            self._add_subdiv_yt_holidays()
        elif self.subdiv == "Nouvelle-Calédonie":
            self._add_subdiv_nc_holidays()
        elif self.subdiv == "Polynésie Française":
            self._add_subdiv_pf_holidays()
        elif self.subdiv == "Saint-Barthélémy":
            self._add_subdiv_bl_holidays()
        elif self.subdiv == "Saint-Martin":
            self._add_subdiv_mf_holidays()
        elif self.subdiv == "Wallis-et-Futuna":
            self._add_subdiv_wf_holidays()

    # Saint Barthelemy.
    def _add_subdiv_bl_holidays(self):
        # Abolition of slavery.
        self._add_holiday(tr("Abolition de l'esclavage"), OCT, 9)

    # Alsace, Champagne-Ardenne, Lorraine(Moselle).
    def _add_subdiv_ges_holidays(self):
        # Good Friday.
        self._add_good_friday(tr("Vendredi saint"))

        # Saint Stephen's Day.
        self._add_christmas_day_two(tr("Saint Étienne"))

    # Guadeloupe.
    def _add_subdiv_gp_holidays(self):
        # Good Friday.
        self._add_good_friday(tr("Vendredi saint"))

        # Mi-Careme.
        self._add_holiday(tr("Mi-Carême"), self._easter_sunday + td(days=-24))

        # Abolition of slavery.
        self._add_holiday(tr("Abolition de l'esclavage"), MAY, 27)

        # Feast of Victor Schoelcher.
        self._add_holiday(tr("Fête de Victor Schoelcher"), JUL, 21)

    # Guyane.
    def _add_subdiv_gy_holidays(self):
        # Abolition of slavery.
        self._add_holiday(tr("Abolition de l'esclavage"), JUN, 10)

    # Saint Martin.
    def _add_subdiv_mf_holidays(self):
        if self._year >= 2018:
            # Abolition of slavery.
            self._add_holiday(tr("Abolition de l'esclavage"), MAY, 28)

    # Martinique.
    def _add_subdiv_mq_holidays(self):
        # Good Friday.
        self._add_good_friday(tr("Vendredi saint"))

        # Abolition of slavery.
        self._add_holiday(tr("Abolition de l'esclavage"), MAY, 22)

        # Feast of Victor Schoelcher.
        self._add_holiday(tr("Fête de Victor Schoelcher"), JUL, 21)

    # New Caledonia.
    def _add_subdiv_nc_holidays(self):
        # Citizenship Day.
        self._add_holiday(tr("Fête de la Citoyenneté"), SEP, 24)

    # French Polynesia.
    def _add_subdiv_pf_holidays(self):
        # Good Friday.
        self._add_good_friday(tr("Vendredi saint"))

        # Missionary Day.
        self._add_holiday(tr("Arrivée de l'Évangile"), MAR, 5)

        # Internal Autonomy Day.
        self._add_holiday(tr("Fête de l'autonomie"), JUN, 29)

    # Reunion.
    def _add_subdiv_re_holidays(self):
        if self._year >= 1981:
            # Abolition of slavery.
            self._add_holiday(tr("Abolition de l'esclavage"), DEC, 20)

    #  Wallis and Futuna.
    def _add_subdiv_wf_holidays(self):
        # Feast of Saint Peter Chanel.
        self._add_holiday(tr("Saint Pierre Chanel"), APR, 28)

        # Festival of the territory.
        self._add_holiday(tr("Fête du Territoire"), JUL, 29)

    # Mayotte.
    def _add_subdiv_yt_holidays(self):
        # Abolition of slavery.
        self._add_holiday(tr("Abolition de l'esclavage"), APR, 27)


class FR(France):
    """FR is also used by dateutil (Friday), so be careful with this one."""

    pass


class FRA(France):
    pass
