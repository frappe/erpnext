from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import CheckMessage
from django.core.checks import Error

from corsheaders.conf import conf

re_type = type(re.compile(""))


def check_settings(**kwargs: Any) -> list[CheckMessage]:
    errors: list[CheckMessage] = []

    if not is_sequence(conf.CORS_ALLOW_HEADERS, str):
        errors.append(
            Error(
                "CORS_ALLOW_HEADERS should be a sequence of strings.",
                id="corsheaders.E001",
            )
        )

    if not is_sequence(conf.CORS_ALLOW_METHODS, str):
        errors.append(
            Error(
                "CORS_ALLOW_METHODS should be a sequence of strings.",
                id="corsheaders.E002",
            )
        )

    if not isinstance(conf.CORS_ALLOW_CREDENTIALS, bool):
        errors.append(  # type: ignore [unreachable]
            Error("CORS_ALLOW_CREDENTIALS should be a bool.", id="corsheaders.E003")
        )

    if not isinstance(conf.CORS_ALLOW_PRIVATE_NETWORK, bool):
        errors.append(  # type: ignore [unreachable]
            Error(
                "CORS_ALLOW_PRIVATE_NETWORK should be a bool.",
                id="corsheaders.E015",
            )
        )

    if (
        not isinstance(conf.CORS_PREFLIGHT_MAX_AGE, int)
        or conf.CORS_PREFLIGHT_MAX_AGE < 0
    ):
        errors.append(
            Error(
                (
                    "CORS_PREFLIGHT_MAX_AGE should be an integer greater than "
                    + "or equal to zero."
                ),
                id="corsheaders.E004",
            )
        )

    if not isinstance(conf.CORS_ALLOW_ALL_ORIGINS, bool):
        if hasattr(settings, "CORS_ALLOW_ALL_ORIGINS"):  # type: ignore [unreachable]
            allow_all_alias = "CORS_ALLOW_ALL_ORIGINS"
        else:
            allow_all_alias = "CORS_ORIGIN_ALLOW_ALL"
        errors.append(
            Error(
                f"{allow_all_alias} should be a bool.",
                id="corsheaders.E005",
            )
        )

    if hasattr(settings, "CORS_ALLOWED_ORIGINS"):
        allowed_origins_alias = "CORS_ALLOWED_ORIGINS"
    else:
        allowed_origins_alias = "CORS_ORIGIN_WHITELIST"

    if not is_sequence(conf.CORS_ALLOWED_ORIGINS, str):
        errors.append(
            Error(
                f"{allowed_origins_alias} should be a sequence of strings.",
                id="corsheaders.E006",
            )
        )
    else:
        special_origin_values = (
            # From 'security sensitive' contexts
            "null",
            # From files on Chrome on Android
            # https://bugs.chromium.org/p/chromium/issues/detail?id=991107
            "file://",
        )
        for origin in conf.CORS_ALLOWED_ORIGINS:
            if origin in special_origin_values:
                continue
            parsed = urlsplit(origin)
            if parsed.scheme == "" or parsed.netloc == "":
                errors.append(
                    Error(
                        "Origin {} in {} is missing scheme or netloc".format(
                            repr(origin), allowed_origins_alias
                        ),
                        id="corsheaders.E013",
                        hint=(
                            "Add a scheme (e.g. https://) or netloc (e.g. "
                            + "example.com)."
                        ),
                    )
                )
            else:
                # Only do this check in this case because if the scheme is not
                # provided, netloc ends up in path
                for part in ("path", "query", "fragment"):
                    if getattr(parsed, part) != "":
                        errors.append(
                            Error(
                                "Origin {} in {} should not have {}".format(
                                    repr(origin), allowed_origins_alias, part
                                ),
                                id="corsheaders.E014",
                            )
                        )

    if hasattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES"):
        allowed_regexes_alias = "CORS_ALLOWED_ORIGIN_REGEXES"
    else:
        allowed_regexes_alias = "CORS_ORIGIN_REGEX_WHITELIST"
    if not is_sequence(conf.CORS_ALLOWED_ORIGIN_REGEXES, (str, re_type)):
        errors.append(
            Error(
                "{} should be a sequence of strings and/or compiled regexes.".format(
                    allowed_regexes_alias
                ),
                id="corsheaders.E007",
            )
        )

    if not is_sequence(conf.CORS_EXPOSE_HEADERS, str):
        errors.append(
            Error("CORS_EXPOSE_HEADERS should be a sequence.", id="corsheaders.E008")
        )

    if not isinstance(conf.CORS_URLS_REGEX, (str, re_type)):
        errors.append(
            Error("CORS_URLS_REGEX should be a string or regex.", id="corsheaders.E009")
        )

    if hasattr(settings, "CORS_MODEL"):
        errors.append(
            Error(
                (
                    "The CORS_MODEL setting has been removed - see "
                    + "django-cors-headers' HISTORY."
                ),
                id="corsheaders.E012",
            )
        )

    if hasattr(settings, "CORS_REPLACE_HTTPS_REFERER"):
        errors.append(
            Error(
                (
                    "The CORS_REPLACE_HTTPS_REFERER setting has been removed"
                    + " - see django-cors-headers' CHANGELOG."
                ),
                id="corsheaders.E013",
            )
        )

    return errors


def is_sequence(thing: Any, type_or_types: type[Any] | tuple[type[Any], ...]) -> bool:
    return isinstance(thing, Sequence) and all(
        isinstance(x, type_or_types) for x in thing
    )
