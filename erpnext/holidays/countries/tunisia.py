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

from holidays.calendars.gregorian import JAN, MAR, APR, JUL, AUG, OCT
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import InternationalHolidays, IslamicHolidays


class Tunisia(HolidayBase, InternationalHolidays, IslamicHolidays):
    """
    Holidays here are estimates, it is common for the day to be pushed
    if falls in a weekend, although not a rule that can be implemented.
    Holidays after 2020: the following four moving date holidays whose exact
    date is announced yearly are estimated (and so denoted):
    - Eid El Fetr
    - Eid El Adha
    - Arafat Day
    - Moulad El Naby
    """

    country = "TN"
    default_language = "ar"
    # Estimated label.
    estimated_label = tr("(تقدير*) *%s")
    supported_languages = ("ar", "en_US")

    def __init__(self, *args, **kwargs):
        InternationalHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day
        self._add_new_years_day(tr("رأس السنة الميلادية"))

        # Revolution and Youth Day - January 14
        self._add_holiday(tr("عيد الثورة والشباب"), JAN, 14)

        # Independence Day
        self._add_holiday(tr("عيد الإستقلال"), MAR, 20)

        # Martyrs' Day
        self._add_holiday(tr("عيد الشهداء"), APR, 9)

        # Labour Day
        self._add_labor_day(tr("عيد العمال"))

        # Republic Day
        self._add_holiday(tr("عيد الجمهورية"), JUL, 25)

        # Women's Day
        self._add_holiday(tr("عيد المرأة"), AUG, 13)

        # Evacuation Day
        self._add_holiday(tr("عيد الجلاء"), OCT, 15)

        # Eid al-Fitr - Feast Festive
        # date of observance is announced yearly, This is an estimate since
        # having the Holiday on Weekend does change the number of days,
        # deceided to leave it since marking a Weekend as a holiday
        # wouldn't do much harm.
        name = tr("عيد الفطر")
        self._add_eid_al_fitr_day(name)
        # Eid al-Fitr Holiday
        self._add_eid_al_fitr_day_two(tr("عطلة عيد الفطر"))
        self._add_eid_al_fitr_day_three(tr("عطلة عيد الفطر"))

        #  Eid al-Adha - Scarfice Festive
        # date of observance is announced yearly
        name = tr("عيد الأضحى")
        # Arafat Day
        self._add_arafah_day(tr("يوم عرفة"))
        self._add_eid_al_adha_day(name)
        # Eid al-Adha Holiday
        self._add_eid_al_adha_day_two(tr("عطلة عيد الأضحى"))
        self._add_eid_al_adha_day_three(tr("عطلة عيد الأضحى"))

        # Islamic New Year - (hijari_year, 1, 1)
        self._add_islamic_new_year_day(tr("رأس السنة الهجرية"))

        # Prophet Muhammad's Birthday - (hijari_year, 3, 12)
        self._add_mawlid_day(tr("عيد المولد النبوي"))


class TN(Tunisia):
    pass


class TUN(Tunisia):
    pass
