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

from holidays.holiday_base import HolidayBase
from holidays.holiday_groups import ChristianHolidays, InternationalHolidays


class Denmark(HolidayBase, ChristianHolidays, InternationalHolidays):
    """
    Denmark holidays.

    References:
    - https://en.wikipedia.org/wiki/Public_holidays_in_Denmark
    - https://www.ft.dk/samling/20222/lovforslag/l13/index.htm
    """

    country = "DK"
    default_language = "da"
    supported_languages = ("da", "en_US", "uk")

    def __init__(self, *args, **kwargs):
        ChristianHolidays.__init__(self)
        InternationalHolidays.__init__(self)
        super().__init__(*args, **kwargs)

    def _populate(self, year):
        super()._populate(year)

        # New Year's Day.
        self._add_new_years_day(tr("Nytårsdag"))

        # Holy Thursday.
        self._add_holy_thursday(tr("Skærtorsdag"))

        # Good Friday.
        self._add_good_friday(tr("Langfredag"))

        # Easter Sunday.
        self._add_easter_sunday(tr("Påskedag"))

        # Easter Monday.
        self._add_easter_monday(tr("Anden påskedag"))

        # See https://www.ft.dk/samling/20222/lovforslag/l13/index.htm
        if year <= 2023:
            # Great Day of Prayers.
            self._add_holiday(tr("Store bededag"), self._easter_sunday + td(days=+26))

        # Ascension Day.
        self._add_ascension_thursday(tr("Kristi himmelfartsdag"))

        # Whit Sunday.
        self._add_whit_sunday(tr("Pinsedag"))

        # Whit Monday.
        self._add_whit_monday(tr("Anden pinsedag"))

        # Christmas Day.
        self._add_christmas_day(tr("Juledag"))

        # Second Day of Christmas.
        self._add_christmas_day_two(tr("Anden juledag"))


class DK(Denmark):
    pass


class DNK(Denmark):
    pass
