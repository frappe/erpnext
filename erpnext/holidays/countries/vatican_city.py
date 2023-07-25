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

from holidays.calendars.gregorian import JAN, FEB, MAR, APR, MAY, OCT, NOV
from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays


class VaticanCity(HolidayBase, ChristianHolidays):
    """
    References:
      - https://en.wikipedia.org/wiki/Public_holidays_in_Vatican_City
      - https://www.ewtn.com/catholicism/library/solemnity-of-mary-mother-of-god-5826
      - https://www.franciscanmedia.org/saint-of-the-day/saint-joseph-the-worker/
    """

    country = "VA"

    def __init__(self, *args, **kwargs) -> None:
        ChristianHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year: int) -> None:
        if year <= 1928:
            return None
        super()._populate(year)

        # Solemnity of Mary Day.
        # This is supposedly the same as International New Year.
        # Modern adoption across the entire Latin Church in 1931 though this
        # was already celebrated in Rome as the Octave day of Christmas.
        self._add_holiday("Solemnity of Mary Day", JAN, 1)

        # Epiphany.
        self._add_epiphany_day("Epiphany")

        # Lateran Treaty Day.
        self._add_holiday("Lateran Treaty Day", FEB, 11)

        if year >= 1978:
            if year >= 2013:
                # Anniversary of the election of Pope Francis.
                dt = (MAR, 13)
            elif year >= 2005:
                # Anniversary of the election of Pope Benedict XVI.
                dt = (APR, 19)
            else:
                # Anniversary of the election of Pope John Paul II.
                dt = (OCT, 16)
            self._add_holiday("Anniversary of the Election of the Holy Father", *dt)

        # In 2005-2013 - also name day for the civilian name of
        # Pope Benedict XVI (Josef Ratzinger)
        # Saint Joseph's Day.
        self._add_saint_josephs_day("Saint Joseph's Day")

        # Easter Sunday.
        self._add_easter_sunday("Easter Sunday")

        # Easter Monday.
        self._add_easter_monday("Easter Monday")

        if year >= 2013:
            # Name day for the civilian name of Pope Francis
            # (Jorge Mario Bergoglio)
            # Saint George's Day.
            self._add_saint_georges_day("Saint George's Day")

        if year >= 1955:
            # Saint Joseph the Worker's Day.
            # Created in response to May Day holidays by Pope Pius XII in 1955.
            self._add_holiday("Saint Joseph the Worker's Day", MAY, 1)

        if year <= 2009:
            # Ascension of Christ.
            self._add_ascension_thursday("Ascension of Christ")

            # Corpus Christi.
            self._add_corpus_christi_day("Corpus Christi")

        # Saints Peter and Paul.
        self._add_saints_peter_and_paul_day("Saint Peter and Saint Paul's Day")

        # Assumption of Mary Day.
        self._add_assumption_of_mary_day("Assumption Day")

        # Nativity Of Mary Day.
        self._add_nativity_of_mary_day("Nativity of Mary Day")

        # All Saints' Day.
        self._add_all_saints_day("All Saints' Day")

        if 1978 <= year <= 2004:
            # Name day for the civilian name of Pope John Paul II
            # (Karol Józef Wojtyła)
            # Saint Charles Borromeo Day.
            self._add_holiday("Saint Charles Borromeo Day", NOV, 4)

        # Immaculate Conception.
        self._add_immaculate_conception_day("Immaculate Conception Day")

        # Christmas Day.
        self._add_christmas_day("Christmas Day")

        # Saint Stephen's Day.
        self._add_christmas_day_two("Saint Stephen's Day")


class VA(VaticanCity):
    pass


class VAT(VaticanCity):
    pass
