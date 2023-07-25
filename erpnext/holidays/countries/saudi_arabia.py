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
from typing import Set

from holidays.calendars.gregorian import JAN, FEB, SEP, NOV, THU, FRI, SAT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import IslamicHolidays


class SaudiArabia(HolidayBase, IslamicHolidays):
    """
    There are only 4 official national holidays in Saudi:
    https://laboreducation.hrsd.gov.sa/en/gallery/274
    https://laboreducation.hrsd.gov.sa/en/labor-education/322
    https://english.alarabiya.net/News/gulf/2022/01/27/Saudi-Arabia-to-commemorate-Founding-Day-on-Feb-22-annually-Royal-order
    The national day and the founding day holidays are based on the
    Georgian calendar while the other two holidays are based on the
    Islamic Calendar, and they are estimates as they announced each
    year and based on moon sightings;
    they are:
        - Eid al-Fitr
        - Eid al-Adha
    """

    country = "SA"
    default_language = "ar"
    # Estimated label.
    estimated_label = tr("(تقدير*) *%s")
    supported_languages = ("ar", "en_US")

    special_holidays = {
        # Celebrate the country's win against Argentina in the World Cup
        2022: (NOV, 23, tr("يوم وطني")),
    }

    def __init__(self, *args, **kwargs):
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _add_islamic_observed(self, hol_name: str, hol_dates: Set[date]) -> None:
        if not self.observed:
            return None
        for dt in hol_dates:
            weekend_days = sum(self._is_weekend(dt + td(days=i)) for i in range(4))
            for i in range(weekend_days):
                self._add_holiday(self.tr("(ملاحظة) %s") % self.tr(hol_name), dt + td(days=+4 + i))

    def _add_observed(self, hol_date: date) -> None:
        if self.observed:
            weekend = sorted(self.weekend)
            # 1st weekend day (Thursday before 2013 and Friday otherwise)
            if hol_date.weekday() == weekend[0]:
                self._add_holiday(
                    self.tr("(ملاحظة) %s") % self.tr(self[hol_date]), hol_date + td(days=-1)
                )
            # 2nd weekend day (Friday before 2013 and Saturday otherwise)
            elif hol_date.weekday() == weekend[1]:
                self._add_holiday(
                    self.tr("(ملاحظة) %s") % self.tr(self[hol_date]), hol_date + td(days=+1)
                )

    def _populate(self, year):
        super()._populate(year)

        # Weekend used to be THU, FRI before June 28th, 2013.
        # On that year both Eids were after that date, and Founding day
        # holiday started at 2022; so what below works.
        self.weekend = {THU, FRI} if year <= 2012 else {FRI, SAT}

        # The holiday is a 4-day holiday starting on the day following the
        # 29th day of Ramadan, the 9th month of the Islamic calendar.
        # Observed days are added to make up for any days falling on a weekend.
        # Holidays may straddle across Gregorian years, so we go back one year
        # to pick up any such occurrence.
        # Date of observance is announced yearly.
        # Eid al-Fitr Holiday
        name = tr("عطلة عيد الفطر")
        dates = self._add_eid_al_fitr_day(name)
        self._add_eid_al_fitr_day_two(name)
        self._add_eid_al_fitr_day_three(name)
        self._add_eid_al_fitr_day_four(name)
        self._add_islamic_observed(name, dates)

        # The holiday is a 4-day holiday starting on Arafat Day, the 10th of
        # Dhu al-Hijjah, the 12th month of the Islamic calendar.
        # Observed days are added to make up for any days falling on a weekend.
        # Holidays may straddle across Gregorian years, so we go back one year
        # to pick up any such occurrence.
        # Date of observance is announced yearly.
        # Arafat Day
        dates = self._add_arafah_day(tr("يوم عرفة"))
        # Eid al-Adha Holiday
        name = tr("عطلة عيد الأضحى")
        self._add_eid_al_adha_day(name)
        self._add_eid_al_adha_day_two(name)
        self._add_eid_al_adha_day_three(name)
        self._add_islamic_observed(name, dates)

        # National Day holiday (started at the year 2005).
        # Note: if national day happens within the Eid al-Fitr Holiday or
        # within Eid al-Fitr Holiday, there is no extra holidays given for it.
        if year >= 2005:
            dt = date(year, SEP, 23)
            if dt not in self:
                # National Day Holiday
                self._add_observed(self._add_holiday(tr("اليوم الوطني"), dt))

        # Founding Day holiday (started 2022).
        # Note: if founding day happens within the Eid al-Fitr Holiday or
        # within Eid al-Fitr Holiday, there is no extra holidays given for it.
        if year >= 2022:
            dt = date(year, FEB, 22)
            if dt not in self:
                # Founding Day
                self._add_observed(self._add_holiday(tr("يوم التأسيسي"), dt))

        # observed holidays special cases
        if self.observed and year == 2001:
            # Eid al-Fitr Holiday (observed)
            self._add_holiday(tr("عطلة عيد الفطر (ملاحظة)"), JAN, 1)


class SA(SaudiArabia):
    pass


class SAU(SaudiArabia):
    pass
