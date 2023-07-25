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

from holidays.calendars.gregorian import GREGORIAN_CALENDAR, JAN, APR, JUN, JUL, AUG, OCT, NOV
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Ukraine(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Current holidays list:
    https://zakon1.rada.gov.ua/laws/show/322-08/paran454#n454
    """

    country = "UA"
    default_language = "uk"
    supported_languages = ("ar", "en_US", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        # The current set of holidays came into force in 1991
        if year <= 1990:
            return None

        # There is no holidays in Ukraine during the period of martial law
        # https://zakon.rada.gov.ua/laws/show/2136-20#n26
        # law is in force from March 15, 2022
        if year >= 2023:
            return None

        super()._populate(year)
        observed_dates = set()

        # New Year's Day.
        observed_dates.add(self._add_new_years_day(tr("Новий рік")))

        observed_dates.add(
            self._add_christmas_day(
                # Christmas (Julian calendar).
                tr("Різдво Христове (за юліанським календарем)")
            )
        )

        # International Women's Day.
        observed_dates.add(self._add_womens_day(tr("Міжнародний жіночий день")))

        # There is no holidays from March 15, 2022
        # https://zakon.rada.gov.ua/laws/show/2136-20#n26
        if year <= 2021:
            # Easter Sunday (Pascha).
            observed_dates.add(self._add_easter_sunday(tr("Великдень (Пасха)")))

            # Holy Trinity Day.
            observed_dates.add(self._add_whit_sunday(tr("Трійця")))

            name = (
                # Labour Day.
                tr("День праці")
                if year >= 2018
                # International Workers' Solidarity Day.
                else tr("День міжнародної солідарності трудящих")
            )
            observed_dates.add(self._add_labor_day(name))
            if year <= 2017:
                observed_dates.add(self._add_labor_day_two(name))

            name = (
                # Day of Victory over Nazism in World War II (Victory Day).
                tr("День перемоги над нацизмом у Другій світовій війні (День перемоги)")
                if year >= 2016
                # Victory Day.
                else tr("День перемоги")
            )
            observed_dates.add(self._add_world_war_two_victory_day(name))

            if year >= 1997:
                observed_dates.add(
                    # Day of the Constitution of Ukraine.
                    self._add_holiday(tr("День Конституції України"), JUN, 28)
                )

            # Independence Day.
            name = tr("День незалежності України")
            if year >= 1992:
                observed_dates.add(self._add_holiday(name, AUG, 24))
            else:
                self._add_holiday(name, JUL, 16)

            if year >= 2015:
                name = (
                    # Day of defenders of Ukraine.
                    tr("День захисників і захисниць України")
                    if year >= 2021
                    # Defender of Ukraine Day.
                    else tr("День захисника України")
                )
                observed_dates.add(self._add_holiday(name, OCT, 14))

            if year <= 1999:
                # Anniversary of the Great October Socialist Revolution.
                name = tr("Річниця Великої Жовтневої соціалістичної революції")
                observed_dates.add(self._add_holiday(name, NOV, 7))
                observed_dates.add(self._add_holiday(name, NOV, 8))

            if year >= 2017:
                observed_dates.add(
                    self._add_christmas_day(
                        # Christmas (Gregorian calendar).
                        tr("Різдво Христове (за григоріанським календарем)"),
                        GREGORIAN_CALENDAR,
                    )
                )

        # 27.01.1995: holiday on weekend move to next workday
        # https://zakon.rada.gov.ua/laws/show/35/95-вр
        # 10.01.1998: cancelled
        # https://zakon.rada.gov.ua/laws/show/785/97-вр
        # 23.04.1999: holiday on weekend move to next workday
        # https://zakon.rada.gov.ua/laws/show/576-14
        if self.observed:
            for dt in sorted(observed_dates):
                if self._is_weekend(dt) and (
                    date(1995, JAN, 27) <= dt <= date(1998, JAN, 9) or dt >= date(1999, APR, 23)
                ):
                    obs_date = dt + td(days=+2 if self._is_saturday(dt) else +1)
                    while obs_date in self:
                        obs_date += td(days=+1)
                    hol_name = self.tr("%s (вихідний)") % self[dt]
                    self._add_holiday(hol_name, obs_date)


class UA(Ukraine):
    pass


class UKR(Ukraine):
    pass
