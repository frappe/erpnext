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


from gettext import gettext as tr

from holidays.calendars.gregorian import JAN, APR, JUN, JUL, OCT
from holidays.calendars.julian import JULIAN_CALENDAR
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, IslamicHolidays, InternationalHolidays


class Egypt(HolidayBase, ChristianHolidays, IslamicHolidays, InternationalHolidays):
    # Holidays here are estimates, it is common for the day to be pushed
    # if falls in a weekend, although not a rule that can be implemented.
    # Holidays after 2020: the following four moving date holidays whose exact
    # date is announced yearly are estimated (and so denoted):
    # - Eid El Fetr*
    # - Eid El Adha*
    # - Arafat Day*
    # - Moulad El Naby*
    # *only if hijri-converter library is installed, otherwise a warning is
    #  raised that this holiday is missing. hijri-converter requires
    #  Python >= 3.6
    # is_weekend function is there, however not activated for accuracy.

    country = "EG"
    default_language = "ar"
    # Estimated label.
    estimated_label = tr("(تقدير*) *%s")
    supported_languages = ("ar", "en_US")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self, JULIAN_CALENDAR)
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)

        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day
        self._add_new_years_day(tr("رأس السنة الميلادية"))

        # Coptic Christmas
        self._add_christmas_day(tr("عيد الميلاد المجيد (تقويم قبطي)"))

        if year >= 2012:
            # January 25th Revolution
            self._add_holiday(tr("عيد ثورة 25 يناير"), JAN, 25)
        elif year >= 2009:
            # National Police Day
            self._add_holiday(tr("عيد الشرطة"), JAN, 25)

        # Coptic Easter - Orthodox Easter
        self._add_easter_sunday(tr("عيد الفصح القبطي"))
        self._add_easter_monday(tr("شم النسيم"))  # Spring Festival

        if year > 1982:
            # Sinai Libration Day
            self._add_holiday(tr("عيد تحرير سيناء"), APR, 25)

        # Labour Day
        self._add_labor_day(tr("عيد العمال"))

        # Armed Forces Day
        self._add_holiday(tr("عيد القوات المسلحة"), OCT, 6)

        if year >= 2014:
            # June 30 Revolution Day
            self._add_holiday(tr("عيد ثورة 30 يونيو"), JUN, 30)

        if year > 1952:
            # July 23 Revolution Day
            self._add_holiday(tr("عيد ثورة 23 يوليو"), JUL, 23)

        # Eid al-Fitr - Feast Festive
        self._add_eid_al_fitr_day(tr("عيد الفطر"))
        # Eid al-Fitr Holiday
        self._add_eid_al_fitr_day_two(tr("عطلة عيد الفطر"))
        self._add_eid_al_fitr_day_three(tr("عطلة عيد الفطر"))

        # Arafat Day
        self._add_arafah_day(tr("يوم عرفة"))

        # Eid al-Adha - Scarfice Festive
        self._add_eid_al_adha_day(tr("عيد الأضحى"))
        # Eid al-Adha Holiday
        self._add_eid_al_adha_day_two(tr("عطلة عيد الأضحى"))
        self._add_eid_al_adha_day_three(tr("عطلة عيد الأضحى"))

        # Islamic New Year
        self._add_islamic_new_year_day(tr("رأس السنة الهجرية"))

        # Prophet Muhammad's Birthday
        self._add_mawlid_day(tr("عيد المولد النبوي"))


class EG(Egypt):
    pass


class EGY(Egypt):
    pass
