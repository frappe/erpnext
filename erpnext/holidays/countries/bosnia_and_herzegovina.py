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
#  Copyright: Kateryna Golovanova <kate@kgthreads.com>, 2022

from datetime import date
from datetime import timedelta as td
from gettext import gettext as tr

from holidays.calendars import _CustomIslamicCalendar
from holidays.calendars.gregorian import GREGORIAN_CALENDAR
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.constants import JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class BosniaAndHerzegovina(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Bosnia_and_Herzegovina
    https://www.paragraf.ba/neradni-dani-fbih.html
    https://www.paragraf.ba/neradni-dani-republike-srpske.html
    https://www.paragraf.ba/neradni-dani-brcko.html
    """

    country = "BA"
    default_language = "bs"
    supported_languages = ("bs", "en_US", "sr", "uk")
    subdivisions = (
        "BIH",  # Federacija Bosne i Hercegovine
        "BRC",  # Brčko distrikt
        "SRP",  # Republika Srpska
    )
    _deprecated_subdivisions = (
        "BD",
        "FBiH",
        "RS",
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self, calendar=BosniaAndHerzegovinaIslamicCalendar())
        super().__init__(*args, **kwargs)

    def _add_observed(
        self, dt: date, include_sat: bool = True, include_sun: bool = True, days: int = +1
    ) -> None:
        # BIH: if first day of New Year's Day and Labor Day fall on Sunday, observed on Tuesday.
        # BRC: if holiday fall on Sunday, observed on next working day.
        # SRP: if second day of New Year's Day and Labor Day fall on Sunday, observed on Monday.
        if not self.observed:
            return None
        if (include_sun and self._is_sunday(dt)) or (include_sat and self._is_saturday(dt)):
            self._add_holiday(
                self.tr("%s (preneseno)") % self[dt],
                dt + td(days=+2 if self._is_saturday(dt) else days),
            )

    def _populate(self, year):
        super()._populate(year)

        # Orthodox Good Friday.
        self._add_good_friday(tr("Veliki petak (Pravoslavni)"))

        # Catholic Easter Monday.
        self._add_easter_monday(tr("Uskrsni ponedjeljak (Katolički)"), GREGORIAN_CALENDAR)

        # Eid al-Fitr.
        self._add_eid_al_fitr_day(tr("Ramazanski Bajram"))

        # Eid al-Adha.
        self._add_eid_al_adha_day(tr("Kurban Bajram"))

        if self.subdiv == "BD":
            self._add_subdiv_brc_holidays()
        elif self.subdiv == "FBiH":
            self._add_subdiv_bih_holidays()
        elif self.subdiv == "RS":
            self._add_subdiv_srp_holidays()

    def _add_subdiv_holidays(self):
        if not self.subdiv:
            # New Year's Day.
            name = tr("Nova godina")
            self._add_new_years_day(name)
            self._add_new_years_day_two(name)

            # Orthodox Christmas.
            self._add_christmas_day(tr("Božić (Pravoslavni)"))

            # Labor Day.
            name = tr("Međunarodni praznik rada")
            self._add_labor_day(name)
            self._add_labor_day_two(name)

            # Catholic Christmas.
            self._add_christmas_day(tr("Božić (Katolički)"), GREGORIAN_CALENDAR)

        super()._add_subdiv_holidays()

    def _add_subdiv_bih_holidays(self):
        # New Year's Day.
        name = tr("Nova godina")
        self._add_observed(self._add_new_years_day(name), include_sat=False, days=+2)
        self._add_new_years_day_two(name)

        # Orthodox Christmas Eve.
        self._add_christmas_eve(tr("Badnji dan (Pravoslavni)"))

        # Orthodox Christmas.
        self._add_christmas_day(tr("Božić (Pravoslavni)"))

        # Independence Day.
        self._add_holiday(tr("Dan nezavisnosti"), MAR, 1)

        # Catholic Good Friday.
        self._add_good_friday(tr("Veliki petak (Katolički)"), GREGORIAN_CALENDAR)

        # Catholic Easter.
        self._add_easter_sunday(tr("Uskrs (Katolički)"), GREGORIAN_CALENDAR)

        # Orthodox Easter.
        self._add_easter_sunday(tr("Vaskrs (Pravoslavni)"))

        # Orthodox Easter Monday.
        self._add_easter_monday(tr("Uskrsni ponedjeljak (Pravoslavni)"))

        # Labor Day.
        name = tr("Međunarodni praznik rada")
        self._add_observed(self._add_labor_day(name), include_sat=False, days=+2)
        self._add_labor_day_two(name)

        # Victory Day.
        self._add_world_war_two_victory_day(tr("Dan pobjede nad fašizmom"))

        # Statehood Day.
        self._add_holiday(tr("Dan državnosti"), NOV, 25)

        # Catholic Christmas Eve.
        self._add_christmas_eve(tr("Badnji dan (Katolički)"), GREGORIAN_CALENDAR)

        # Catholic Christmas.
        self._add_christmas_day(tr("Božić (Katolički)"), GREGORIAN_CALENDAR)

        # Eid al-Fitr.
        self._add_eid_al_fitr_day_two(tr("Ramazanski Bajram"))

        # Eid al-Adha.
        self._add_eid_al_adha_day_two(tr("Kurban Bajram"))

    def _add_subdiv_brc_holidays(self):
        # New Year's Day.
        name = tr("Nova godina")
        self._add_observed(self._add_new_years_day(name), days=+2)
        self._add_new_years_day_two(name)

        # Orthodox Christmas.
        self._add_observed(self._add_christmas_day(tr("Božić (Pravoslavni)")), include_sat=False)

        self._add_observed(
            # Day of establishment of Brčko District.
            self._add_holiday(tr("Dan uspostavljanja Brčko distrikta"), MAR, 8),
            include_sat=False,
        )

        # Labor Day.
        name = tr("Međunarodni praznik rada")
        self._add_observed(self._add_labor_day(name), days=+2)
        self._add_labor_day_two(name)

        self._add_observed(
            # Catholic Christmas.
            self._add_christmas_day(tr("Božić (Katolički)"), GREGORIAN_CALENDAR),
            include_sat=False,
        )

    def _add_subdiv_srp_holidays(self):
        # New Year's Day.
        name = tr("Nova godina")
        self._add_observed(self._add_new_years_day(name), include_sun=False)
        self._add_new_years_day_two(name)

        # Orthodox Christmas Eve.
        self._add_christmas_eve(tr("Badnji dan (Pravoslavni)"))

        # Orthodox Christmas.
        self._add_christmas_day(tr("Božić (Pravoslavni)"))

        # Orthodox New Year.
        self._add_holiday(tr("Pravoslavna Nova godina"), JAN, 14)

        # Catholic Good Friday.
        self._add_good_friday(tr("Veliki petak (Katolički)"), GREGORIAN_CALENDAR)

        # Catholic Easter.
        self._add_easter_sunday(tr("Uskrs (Katolički)"), GREGORIAN_CALENDAR)

        # Orthodox Easter.
        self._add_easter_sunday(tr("Vaskrs (Pravoslavni)"))

        # Orthodox Easter Monday.
        self._add_easter_monday(tr("Uskrsni ponedjeljak (Pravoslavni)"))

        # Labor Day.
        name = tr("Međunarodni praznik rada")
        self._add_observed(self._add_labor_day(name), include_sun=False)
        self._add_labor_day_two(name)

        # Victory Day.
        self._add_world_war_two_victory_day(tr("Dan pobjede nad fašizmom"))

        self._add_holiday(
            # Dayton Agreement Day.
            tr("Dan uspostave Opšteg okvirnog sporazuma za mir u Bosni i Hercegovini"),
            NOV,
            21,
        )

        # Catholic Christmas Eve.
        self._add_christmas_eve(tr("Badnji dan (Katolički)"), GREGORIAN_CALENDAR)

        # Catholic Christmas.
        self._add_christmas_day(tr("Božić (Katolički)"), GREGORIAN_CALENDAR)

        # Eid al-Fitr.
        self._add_eid_al_fitr_day_two(tr("Ramazanski Bajram"))

        # Eid al-Adha.
        self._add_eid_al_adha_day_two(tr("Kurban Bajram"))


class BA(BosniaAndHerzegovina):
    pass


class BIH(BosniaAndHerzegovina):
    pass


class BosniaAndHerzegovinaIslamicCalendar(_CustomIslamicCalendar):
    EID_AL_ADHA_DATES = {
        2001: (MAR, 6),
        2002: (FEB, 23),
        2003: (FEB, 12),
        2004: (FEB, 2),
        2005: (JAN, 21),
        2006: ((JAN, 10), (DEC, 31)),
        2007: (DEC, 20),
        2008: (DEC, 9),
        2009: (NOV, 28),
        2010: (NOV, 17),
        2011: (NOV, 7),
        2012: (OCT, 26),
        2013: (OCT, 15),
        2014: (OCT, 4),
        2015: (SEP, 24),
        2016: (SEP, 13),
        2017: (SEP, 2),
        2018: (AUG, 22),
        2019: (AUG, 11),
        2020: (JUL, 31),
        2021: (JUL, 20),
        2022: (JUL, 9),
        2023: (JUN, 28),
    }

    EID_AL_FITR_DATES = {
        2001: (DEC, 17),
        2002: (DEC, 6),
        2003: (NOV, 26),
        2004: (NOV, 14),
        2005: (NOV, 4),
        2006: (OCT, 24),
        2007: (OCT, 13),
        2008: (OCT, 2),
        2009: (SEP, 21),
        2010: (SEP, 10),
        2011: (AUG, 31),
        2012: (AUG, 19),
        2013: (AUG, 8),
        2014: (JUL, 28),
        2015: (JUL, 18),
        2016: (JUL, 7),
        2017: (JUN, 26),
        2018: (JUN, 15),
        2019: (JUN, 4),
        2020: (MAY, 24),
        2021: (MAY, 13),
        2022: (MAY, 2),
        2023: (APR, 21),
    }
