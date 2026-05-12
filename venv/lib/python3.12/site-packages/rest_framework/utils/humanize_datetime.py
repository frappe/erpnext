"""
Helper functions that convert strftime formats into more readable representations.
"""
from rest_framework import ISO_8601


def datetime_formats(formats):
    format = ', '.join(formats).replace(
        ISO_8601,
        'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]'
    )
    return humanize_strptime(format)


def date_formats(formats):
    format = ', '.join(formats).replace(ISO_8601, 'YYYY-MM-DD')
    return humanize_strptime(format)


def time_formats(formats):
    format = ', '.join(formats).replace(ISO_8601, 'hh:mm[:ss[.uuuuuu]]')
    return humanize_strptime(format)


def humanize_strptime(format_string):
    # Note that we're missing some of the locale specific mappings that
    # don't really make sense.
    mapping = {
        "%Y": "YYYY",
        "%y": "YY",
        "%m": "MM",
        "%b": "[Jan-Dec]",
        "%B": "[January-December]",
        "%d": "DD",
        "%H": "hh",
        "%I": "hh",  # Requires '%p' to differentiate from '%H'.
        "%M": "mm",
        "%S": "ss",
        "%f": "uuuuuu",
        "%a": "[Mon-Sun]",
        "%A": "[Monday-Sunday]",
        "%p": "[AM|PM]",
        "%z": "[+HHMM|-HHMM]"
    }
    for key, val in mapping.items():
        format_string = format_string.replace(key, val)
    return format_string
