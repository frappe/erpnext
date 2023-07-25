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


class _CustomCalendarType(type):
    """Helper class for simple calendar customization.

    Renames child class public attributes keeping the original data under a new
    name with a `CUSTOM_ATTR_POSTFIX` postfix.

    Allows for better readability of customized lunisolar calendar dates.
    """

    CUSTOM_ATTR_POSTFIX = "CUSTOM_CALENDAR"

    def __new__(cls, name, bases, namespace):
        for attr in (key for key in tuple(namespace.keys()) if key[0] != "_"):
            namespace[f"{attr}_{_CustomCalendar.CUSTOM_ATTR_POSTFIX}"] = namespace[attr]
            del namespace[attr]

        return super().__new__(cls, name, bases, namespace)


class _CustomCalendar(metaclass=_CustomCalendarType):
    pass
