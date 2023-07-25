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

from holidays.constants import MAY, JUL, SEP, NOV, SUN
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Latvia(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    https://en.wikipedia.org/wiki/Public_holidays_in_Latvia
    https://information.lv/
    https://likumi.lv/ta/id/72608-par-svetku-atceres-un-atzimejamam-dienam
    """

    country = "LV"
    default_language = "lv"

    # General Latvian Song and Dance Festival closing day.
    song_and_dance_festival_closing_day = tr(
        "Vispārējo latviešu Dziesmu un deju svētku noslēguma dienu"
    )
    # Day of His Holiness Pope Francis' pastoral visit to Latvia.
    pope_francis_pastoral_visit_day = tr(
        "Viņa Svētības pāvesta Franciska pastorālās vizītes Latvijā diena"
    )
    # Day the Latvian hockey team won the bronze medal at the 2023 World Ice Hockey Championship.
    hockey_team_win_bronze_medal_day = tr(
        "Diena, kad Latvijas hokeja komanda ieguva bronzas medaļu 2023. gada "
        "Pasaules hokeja čempionātā"
    )
    special_holidays = {
        2018: (
            (JUL, 9, song_and_dance_festival_closing_day),
            (SEP, 24, pope_francis_pastoral_visit_day),
        ),
        2023: (
            (MAY, 29, hockey_team_win_bronze_medal_day),
            (JUL, 10, song_and_dance_festival_closing_day),
        ),
    }

    supported_languages = ("en_US", "lv", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_observed(self, dt: date) -> None:
        if self.observed and self._is_weekend(dt):
            self._add_holiday(
                self.tr("%s (brīvdiena)") % self[dt],
                dt + td(days=+2 if self._is_saturday(dt) else +1),
            )

    def _populate(self, year):
        if year <= 1989:
            return None
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Jaunais Gads"))

        # Good Friday.
        self._add_good_friday(tr("Lielā Piektdiena"))

        # Easter.
        self._add_easter_sunday(tr("Lieldienas"))

        # Easter Monday.
        self._add_easter_monday(tr("Otrās Lieldienas"))

        # Labor Day.
        self._add_labor_day(tr("Darba svētki"))

        if year >= 2002:
            dt = self._add_holiday(
                # Restoration of Independence Day.
                tr("Latvijas Republikas Neatkarības atjaunošanas diena"),
                MAY,
                4,
            )
            if year >= 2008:
                self._add_observed(dt)

        # Mother's Day.
        self._add_holiday(tr("Mātes diena"), self._get_nth_weekday_of_month(2, SUN, MAY))

        # Midsummer Day.
        jun_24 = self._add_saint_johns_day(tr("Jāņu diena"))

        # Midsummer Eve.
        self._add_holiday(tr("Līgo diena"), jun_24 + td(days=-1))

        # Republic of Latvia Proclamation Day.
        dt = self._add_holiday(tr("Latvijas Republikas proklamēšanas diena"), NOV, 18)
        if year >= 2007:
            self._add_observed(dt)

        if year >= 2007:
            # Christmas Eve.
            self._add_christmas_eve(tr("Ziemassvētku vakars"))

        # Christmas Day.
        self._add_christmas_day(tr("Ziemassvētki"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Otrie Ziemassvētki"))

        # New Year's Eve.
        self._add_new_years_eve(tr("Vecgada vakars"))


class LV(Latvia):
    pass


class LVA(Latvia):
    pass
