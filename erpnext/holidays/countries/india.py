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

import warnings

from holidays.calendars.gregorian import JAN, MAR, APR, MAY, JUN, AUG, OCT, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays, IslamicHolidays


class India(HolidayBase, ChristianHolidays, InternationalHolidays, IslamicHolidays):
    """
    https://www.india.gov.in/calendar
    https://www.india.gov.in/state-and-ut-holiday-calendar
    https://en.wikipedia.org/wiki/Public_holidays_in_India
    https://www.calendarlabs.com/holidays/india/2021
    https://slusi.dacnet.nic.in/watershedatlas/list_of_state_abbreviation.htm
    https://vahan.parivahan.gov.in/vahan4dashboard/
    """

    country = "IN"
    subdivisions = (
        "AN",  # Andaman and Nicobar Islands.
        "AP",  # Andhra Pradesh.
        "AR",  # Arunachal Pradesh.
        "AS",  # Assam.
        "BR",  # Bihar.
        "CG",  # Chhattisgarh.
        "CH",  # Chandigarh.
        "DD",  # Daman and Diu.
        "DH",  # Dadra and Nagar Haveli.
        "DL",  # Delhi.
        "GA",  # Goa.
        "GJ",  # Gujarat.
        "HP",  # Himachal Pradesh.
        "HR",  # Haryana.
        "JH",  # Jharkhand.
        "JK",  # Jammu and Kashmir.
        "KA",  # Karnataka.
        "KL",  # Kerala.
        "LA",  # Ladakh.
        "LD",  # Lakshadweep.
        "MH",  # Maharashtra.
        "ML",  # Meghalaya.
        "MN",  # Manipur.
        "MP",  # Madhya Pradesh.
        "MZ",  # Mizoram.
        "NL",  # Nagaland.
        "OR",  # Orissa / Odisha (Govt sites (dacnet/vahan) use code "OR").
        "PB",  # Punjab.
        "PY",  # Pondicherry.
        "RJ",  # Rajasthan.
        "SK",  # Sikkim.
        "TN",  # Tamil Nadu.
        "TR",  # Tripura.
        "TS",  # Telangana.
        "UK",  # Uttarakhand.
        "UP",  # Uttar Pradesh.
        "WB",  # West Bengal.
    )

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        IslamicHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # Makar Sankranti / Pongal.
        self._add_holiday("Makar Sankranti / Pongal", JAN, 14)

        if year >= 1950:
            # Republic Day.
            self._add_holiday("Republic Day", JAN, 26)

        if year >= 1947:
            # Independence Day.
            self._add_holiday("Independence Day", AUG, 15)

        # Gandhi Jayanti.
        self._add_holiday("Gandhi Jayanti", OCT, 2)

        # Labour Day.
        self._add_labor_day("Labour Day")

        # Directly lifted Diwali and Holi dates from FBProphet from:
        # https://github.com/facebook/prophet/blob/main/python/prophet/hdays.py
        # Warnings kept in place so that users are aware
        if year < 2001 or year > 2030:
            warning_msg = "Diwali and Holi holidays available from 2001 to 2030 only"
            warnings.warn(warning_msg, Warning)

        # https://www.timeanddate.com/holidays/india/diwali
        diwali_dates = {
            2001: (NOV, 14),
            2002: (NOV, 4),
            2003: (OCT, 25),
            2004: (NOV, 12),
            2005: (NOV, 1),
            2006: (OCT, 21),
            2007: (NOV, 9),
            2008: (OCT, 28),
            2009: (OCT, 17),
            2010: (NOV, 5),
            2011: (OCT, 26),
            2012: (NOV, 13),
            2013: (NOV, 3),
            2014: (OCT, 23),
            2015: (NOV, 11),
            2016: (OCT, 30),
            2017: (OCT, 19),
            2018: (NOV, 7),
            2019: (OCT, 27),
            2020: (NOV, 14),
            2021: (NOV, 4),
            2022: (OCT, 24),
            2023: (NOV, 12),
            2024: (NOV, 1),
            2025: (OCT, 20),
            2026: (NOV, 8),
            2027: (OCT, 29),
            2028: (OCT, 17),
            2029: (NOV, 5),
            2030: (OCT, 26),
        }

        # https://www.timeanddate.com/holidays/india/holi
        holi_dates = {
            2001: (MAR, 10),
            2002: (MAR, 29),
            2003: (MAR, 18),
            2004: (MAR, 7),
            2005: (MAR, 26),
            2006: (MAR, 15),
            2007: (MAR, 4),
            2008: (MAR, 22),
            2009: (MAR, 11),
            2010: (MAR, 1),
            2011: (MAR, 20),
            2012: (MAR, 8),
            2013: (MAR, 27),
            2014: (MAR, 17),
            2015: (MAR, 6),
            2016: (MAR, 24),
            2017: (MAR, 13),
            2018: (MAR, 2),
            2019: (MAR, 21),
            2020: (MAR, 10),
            2021: (MAR, 29),
            2022: (MAR, 18),
            2023: (MAR, 8),
            2024: (MAR, 25),
            2025: (MAR, 14),
            2026: (MAR, 4),
            2027: (MAR, 22),
            2028: (MAR, 11),
            2029: (MAR, 1),
            2030: (MAR, 20),
        }

        if year in diwali_dates:
            self._add_holiday("Diwali", *diwali_dates[year])

        if year in holi_dates:
            self._add_holiday("Holi", *holi_dates[year])

        # Islamic holidays.
        # Day of Ashura.
        self._add_ashura_day("Day of Ashura")

        # Birth of the Prophet.
        self._add_mawlid_day("Mawlid")

        # Eid ul-Fitr.
        name = "Eid ul-Fitr"
        self._add_eid_al_fitr_day(name)
        self._add_eid_al_fitr_day_two(name)

        # Eid al-Adha.
        name = "Eid al-Adha"
        self._add_eid_al_adha_day(name)
        self._add_eid_al_adha_day_two(name)

        # Christian holidays.
        self._add_palm_sunday("Palm Sunday")
        self._add_good_friday("Good Friday")
        self._add_easter_sunday("Easter Sunday")
        self._add_whit_sunday("Feast of Pentecost")
        self._add_christmas_day("Christmas Day")

    # Andhra Pradesh.
    def _add_subdiv_ap_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Andhra Pradesh Foundation Day", NOV, 1)

    # Assam.
    def _add_subdiv_as_holidays(self):
        self._add_holiday("Bihu (Assamese New Year)", APR, 15)

    # Bihar.
    def _add_subdiv_br_holidays(self):
        self._add_holiday("Bihar Day", MAR, 22)
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)

    # Chhattisgarh.
    def _add_subdiv_cg_holidays(self):
        self._add_holiday("Chhattisgarh Foundation Day", NOV, 1)

    # Gujarat.
    def _add_subdiv_gj_holidays(self):
        self._add_holiday("Uttarayan", JAN, 14)
        self._add_holiday("Gujarat Day", MAY, 1)
        self._add_holiday("Sardar Patel Jayanti", OCT, 31)

    # Haryana.
    def _add_subdiv_hr_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Haryana Foundation Day", NOV, 1)

    # Karnataka.
    def _add_subdiv_ka_holidays(self):
        self._add_holiday("Karnataka Rajyotsava", NOV, 1)

    # Kerala.
    def _add_subdiv_kl_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Kerala Foundation Day", NOV, 1)

    # Maharashtra.
    def _add_subdiv_mh_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Maharashtra Day", MAY, 1)
        self._add_holiday("Dussehra", OCT, 15)

    # Madhya Pradesh.
    def _add_subdiv_mp_holidays(self):
        self._add_holiday("Madhya Pradesh Foundation Day", NOV, 1)

    # Orissa / Odisha.
    def _add_subdiv_or_holidays(self):
        self._add_holiday("Odisha Day (Utkala Dibasa)", APR, 1)
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Maha Vishuva Sankranti / Pana Sankranti", APR, 15)

    # Rajasthan.
    def _add_subdiv_rj_holidays(self):
        self._add_holiday("Rajasthan Day", MAR, 30)
        self._add_holiday("Maharana Pratap Jayanti", JUN, 15)

    # Sikkim.
    def _add_subdiv_sk_holidays(self):
        self._add_holiday("Annexation Day", MAY, 16)

    # Tamil Nadu.
    def _add_subdiv_tn_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Puthandu (Tamil New Year)", APR, 14)
        self._add_holiday("Puthandu (Tamil New Year)", APR, 15)

    # Telangana.
    def _add_subdiv_ts_holidays(self):
        self._add_holiday("Eid al-Fitr", APR, 6)
        self._add_holiday("Bathukamma Festival", OCT, 6)

    # Uttarakhand.
    def _add_subdiv_uk_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)

    # Uttar Pradesh.
    def _add_subdiv_up_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)

    # West Bengal.
    def _add_subdiv_wb_holidays(self):
        self._add_holiday("Dr. B. R. Ambedkar's Jayanti", APR, 14)
        self._add_holiday("Pohela Boishakh", APR, 14)
        self._add_holiday("Pohela Boishakh", APR, 15)
        self._add_holiday("Rabindra Jayanti", MAY, 9)


class IN(India):
    pass


class IND(India):
    pass
