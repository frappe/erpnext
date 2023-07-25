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

__all__ = (
    "country_holidays",
    "CountryHoliday",
    "financial_holidays",
    "list_localized_countries",
    "list_localized_financial",
    "list_supported_countries",
    "list_supported_financial",
)

import warnings
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple, Union

from holidays.holiday_base import HolidayBase
from holidays.registry import EntityLoader


def country_holidays(
    country: str,
    subdiv: Optional[str] = None,
    years: Optional[Union[int, Iterable[int]]] = None,
    expand: bool = True,
    observed: bool = True,
    prov: Optional[str] = None,
    state: Optional[str] = None,
    language: Optional[str] = None,
    categories: Optional[Tuple[str]] = None,
) -> HolidayBase:
    """
    Returns a new dictionary-like :py:class:`HolidayBase` object for the public
    holidays of the country matching **country** and other keyword arguments.

    :param country:
        An ISO 3166-1 Alpha-2 country code.

    :param subdiv:
        The subdivision (e.g. state or province); not implemented for all
        countries (see documentation).

    :param years:
        The year(s) to pre-calculate public holidays for at instantiation.

    :param expand:
        Whether the entire year is calculated when one date from that year
        is requested.

    :param observed:
        Whether to include the dates of when public holiday are observed
        (e.g. a holiday falling on a Sunday being observed the following
        Monday). False may not work for all countries.

    :param prov:
        *deprecated* use subdiv instead.

    :param state:
        *deprecated* use subdiv instead.

    :param language:
        The language which the returned holiday names will be translated
        into. It must be an ISO 639-1 (2-letter) language code. If the
        language translation is not supported the original holiday names
        will be used.

    :param categories:
        Requested holiday categories.

    :return:
        A :py:class:`HolidayBase` object matching the **country**.

    The key of the :class:`dict`-like :class:`HolidayBase` object is the
    `date` of the holiday, and the value is the name of the holiday itself.
    Dates where a key is not present are not public holidays (or, if
    **observed** is False, days when a public holiday is observed).

    When passing the `date` as a key, the `date` can be expressed in one of the
    following types:

    * :class:`datetime.date`,
    * :class:`datetime.datetime`,
    * a :class:`str` of any format recognized by :func:`dateutil.parser.parse`,
    * or a :class:`float` or :class:`int` representing a POSIX timestamp.

    The key is always returned as a :class:`datetime.date` object.

    To maximize speed, the list of public holidays is built on the fly as
    needed, one calendar year at a time. When the object is instantiated
    without a **years** parameter, it is empty, but, unless **expand** is set
    to False, as soon as a key is accessed the class will calculate that entire
    year's list of holidays and set the keys with them.

    If you need to list the holidays as opposed to querying individual dates,
    instantiate the class with the **years** parameter.

    Example usage:

    >>> from holidays import country_holidays
    >>> us_holidays = country_holidays('US')
    # For a specific subdivision (e.g. state or province):
    >>> calif_holidays = country_holidays('US', subdiv='CA')

    The below will cause 2015 holidays to be calculated on the fly:

    >>> from datetime import date
    >>> assert date(2015, 1, 1) in us_holidays

    This will be faster because 2015 holidays are already calculated:

    >>> assert date(2015, 1, 2) not in us_holidays

    The :class:`HolidayBase` class also recognizes strings of many formats
    and numbers representing a POSIX timestamp:

    >>> assert '2014-01-01' in us_holidays
    >>> assert '1/1/2014' in us_holidays
    >>> assert 1388597445 in us_holidays

    Show the holiday's name:

    >>> us_holidays.get('2014-01-01')
    "New Year's Day"

    Check a range:

    >>> us_holidays['2014-01-01': '2014-01-03']
    [datetime.date(2014, 1, 1)]

    List all 2020 holidays:

    >>> us_holidays = country_holidays('US', years=2020)
    >>> for day in us_holidays.items():
    ...     print(day)
    (datetime.date(2020, 1, 1), "New Year's Day")
    (datetime.date(2020, 1, 20), 'Martin Luther King Jr. Day')
    (datetime.date(2020, 2, 17), "Washington's Birthday")
    (datetime.date(2020, 5, 25), 'Memorial Day')
    (datetime.date(2020, 7, 4), 'Independence Day')
    (datetime.date(2020, 7, 3), 'Independence Day (Observed)')
    (datetime.date(2020, 9, 7), 'Labor Day')
    (datetime.date(2020, 10, 12), 'Columbus Day')
    (datetime.date(2020, 11, 11), 'Veterans Day')
    (datetime.date(2020, 11, 26), 'Thanksgiving')
    (datetime.date(2020, 12, 25), 'Christmas Day')

    Some holidays are only present in parts of a country:

    >>> us_pr_holidays = country_holidays('US', subdiv='PR')
    >>> assert '2018-01-06' not in us_holidays
    >>> assert '2018-01-06' in us_pr_holidays

    Append custom holiday dates by passing one of:

    * a :class:`dict` with date/name key/value pairs (e.g.
      ``{'2010-07-10': 'My birthday!'}``),
    * a list of dates (as a :class:`datetime.date`, :class:`datetime.datetime`,
      :class:`str`, :class:`int`, or :class:`float`); ``'Holiday'`` will be
      used as a description,
    * or a single date item (of one of the types above); ``'Holiday'`` will be
      used as a description:

    >>> custom_holidays = country_holidays('US', years=2015)
    >>> custom_holidays.update({'2015-01-01': "New Year's Day"})
    >>> custom_holidays.update(['2015-07-01', '07/04/2015'])
    >>> custom_holidays.update(date(2015, 12, 25))
    >>> assert date(2015, 1, 1) in custom_holidays
    >>> assert date(2015, 1, 2) not in custom_holidays
    >>> assert '12/25/2015' in custom_holidays

    For more complex logic, like 4th Monday of January, you can inherit the
    :class:`HolidayBase` class and define your own :meth:`_populate` method.
    See documentation for examples.
    """
    import holidays

    try:
        return getattr(holidays, country)(
            years=years,
            subdiv=subdiv,
            expand=expand,
            observed=observed,
            prov=prov,
            state=state,
            language=language,
            categories=categories,
        )
    except AttributeError:
        raise NotImplementedError(f"Country {country} not available")


def financial_holidays(
    market: str,
    subdiv: Optional[str] = None,
    years: Optional[Union[int, Iterable[int]]] = None,
    expand: bool = True,
    observed: bool = True,
    language: Optional[str] = None,
) -> HolidayBase:
    """
    Returns a new dictionary-like :py:class:`HolidayBase` object for the public
    holidays of the financial market matching **market** and other keyword
    arguments.

    :param market:
        An ISO 3166-1 Alpha-2 market code.

    :param subdiv:
        Currently not implemented for markets (see documentation).

    :param years:
        The year(s) to pre-calculate public holidays for at instantiation.

    :param expand:
        Whether the entire year is calculated when one date from that year
        is requested.

    :param observed:
        Whether to include the dates of when public holiday are observed
        (e.g. a holiday falling on a Sunday being observed the following
        Monday). False may not work for all countries.

    :param language:
        The language which the returned holiday names will be translated
        into. It must be an ISO 639-1 (2-letter) language code. If the
        language translation is not supported the original holiday names
        will be used.

    :return:
        A :py:class:`HolidayBase` object matching the **market**.

    Example usage:

    >>> from holidays import financial_holidays
    >>> nyse_holidays = financial_holidays('NYSE')

    See :py:func:`country_holidays` documentation for further details and
    examples.
    """
    import holidays

    try:
        return getattr(holidays, market)(
            years=years,
            subdiv=subdiv,
            expand=expand,
            observed=observed,
            language=language,
        )
    except AttributeError:
        raise NotImplementedError(f"Financial market {market} not available")


def CountryHoliday(
    country: str,
    subdiv: Optional[str] = None,
    years: Optional[Union[int, Iterable[int]]] = None,
    expand: bool = True,
    observed: bool = True,
    prov: Optional[str] = None,
    state: Optional[str] = None,
) -> HolidayBase:
    """
    Deprecated name for :py:func:`country_holidays`.

    :meta private:
    """

    warnings.warn(
        "CountryHoliday is deprecated, use country_holidays instead.", DeprecationWarning
    )
    return country_holidays(country, subdiv, years, expand, observed, prov, state)


def _list_localized_entities(entity_codes: Iterable[str]) -> Dict[str, List[str]]:
    """
    Get all localized entities and languages they support.

    :param entity_codes:
        A list of entity codes.

    :return:
        A dictionary where key is an entity code and
        value is a list of supported languages (either ISO 639-1 or a
        combination of ISO 639-1 and ISO 3166-1 codes joined with "_").
    """
    import holidays

    localized_countries = {}
    for entity_code in entity_codes:
        languages = getattr(holidays, entity_code).supported_languages
        if len(languages) == 0:
            continue
        localized_countries[entity_code] = sorted(languages)

    return localized_countries


@lru_cache()
def list_localized_countries(include_aliases=True) -> Dict[str, List[str]]:
    """
    Get all localized countries and languages they support.

    :param include_aliases:
        Whether to include entity aliases (e.g. UK for GB).

    :return:
        A dictionary where key is an ISO 3166-1 alpha-2 country code and
        value is a list of supported languages (either ISO 639-1 or a
        combination of ISO 639-1 and ISO 3166-1 codes joined with "_").
    """

    return _list_localized_entities(EntityLoader.get_country_codes(include_aliases))


@lru_cache()
def list_localized_financial(include_aliases=True) -> Dict[str, List[str]]:
    """
    Get all localized financial markets and languages they support.

    :param include_aliases:
        Whether to include entity aliases(e.g. TAR for ECB, XNYS for NYSE).

    :return:
        A dictionary where key is a market code and value is a list of
        supported subdivision codes.
    """

    return _list_localized_entities(EntityLoader.get_financial_codes(include_aliases))


def _list_supported_entities(entity_codes: Iterable[str]) -> Dict[str, List[str]]:
    """
    Get all supported entities and their subdivisions.

    :param entity_codes:
        A list of entity codes.

    :return:
        A dictionary where key is an entity code and value is a list
        of supported subdivision codes.
    """
    import holidays

    return {
        country_code: list(getattr(holidays, country_code).subdivisions)
        for country_code in entity_codes
    }


@lru_cache()
def list_supported_countries(include_aliases=True) -> Dict[str, List[str]]:
    """
    Get all supported countries and their subdivisions.

    :param include_aliases:
        Whether to include entity aliases (e.g. UK for GB).

    :return:
        A dictionary where key is an ISO 3166-1 alpha-2 country code and
        value is a list of supported subdivision codes.
    """
    return _list_supported_entities(EntityLoader.get_country_codes(include_aliases))


@lru_cache()
def list_supported_financial(include_aliases=True) -> Dict[str, List[str]]:
    """
    Get all supported financial markets and their subdivisions.

    :param include_aliases:
        Whether to include entity aliases(e.g. TAR for ECB, XNYS for NYSE).

    :return:
        A dictionary where key is a market code and value is a list of
        supported subdivision codes.
    """
    return _list_supported_entities(EntityLoader.get_financial_codes(include_aliases))
