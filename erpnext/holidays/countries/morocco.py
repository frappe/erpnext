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

from holidays.calendars.gregorian import JAN, MAR, JUL, AUG, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import IslamicHolidays, InternationalHolidays


class Morocco(HolidayBase, InternationalHolidays, IslamicHolidays):
    """
    Moroccan holidays
    Note that holidays falling on a sunday is "lost",
    it will not be moved to another day to make up for the collision.

    Holidays after 2020: the following four moving date holidays whose exact
    date is announced yearly are estimated (and so denoted):
    - Eid El Fetr
    - Eid El Adha
    - 1er Moharram
    - Aid al Mawlid Annabawi
    Primary sources:
    https://fr.wikipedia.org/wiki/F%C3%AAtes_et_jours_f%C3%A9ri%C3%A9s_au_Maroc
    https://www.mmsp.gov.ma/fr/pratiques.aspx?id=38
    """

    country = "MA"
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

        if year >= 1945:
            # Independence Manifesto Day post 1944
            self._add_holiday(tr("ذكرى تقديم وثيقة الاستقلال"), JAN, 11)

        # In May 2023, Morocco recognised Berber New Year as official holiday
        # http://www.diplomatie.ma/en/statement-royal-office-12
        if year >= 2024:
            # Amazigh New Year
            self._add_holiday(tr("رأس السنة الأمازيغية"), JAN, 13)

        # Labor day
        self._add_labor_day(tr("عيد العمال"))

        if year >= 2001:
            dt = (JUL, 30)
        elif year >= 1963:
            dt = (MAR, 3)
        else:
            dt = (NOV, 18)
        # Throne day
        self._add_holiday(tr("عيد العرش"), *dt)

        # Oued Ed-Dahab Day
        self._add_holiday(tr("ذكرى استرجاع إقليم وادي الذهب"), AUG, 14)

        # Revolution Day
        self._add_holiday(tr("ذكرى ثورة الملك و الشعب"), AUG, 20)

        # Youth day
        self._add_holiday(tr("عيد الشباب"), *((AUG, 21) if year >= 2001 else (JUL, 9)))

        if year >= 1976:
            # Green March
            self._add_holiday(tr("ذكرى المسيرة الخضراء"), NOV, 6)

        if year >= 1957:
            # Independance day
            self._add_holiday(tr("عيد الإستقلال"), NOV, 18)

        # Eid al-Fitr - Feast Festive
        # date of observance is announced yearly, This is an estimate since
        # having the Holiday on Weekend does change the number of days,
        # deceided to leave it since marking a Weekend as a holiday
        # wouldn't do much harm.
        name = tr("عيد الفطر")
        self._add_eid_al_fitr_day(name)
        self._add_eid_al_fitr_day_two(name)

        # Eid al-Adha - Sacrifice Festive
        # date of observance is announced yearly
        name = tr("عيد الأضحى")
        self._add_eid_al_adha_day(name)
        self._add_eid_al_adha_day_two(name)

        # Islamic New Year - (hijari_year, 1, 1)
        self._add_islamic_new_year_day(tr("رأس السنة الهجرية"))

        # Prophet Muhammad's Birthday - (hijari_year, 3, 12)
        name = tr("عيد المولد النبوي")
        self._add_mawlid_day(name)
        self._add_mawlid_day_two(name)


class MA(Morocco):
    pass


class MOR(Morocco):
    pass
