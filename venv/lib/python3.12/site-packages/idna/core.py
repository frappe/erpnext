import bisect
import re
import unicodedata
import warnings
from typing import Optional, Union

from . import idnadata
from .intranges import intranges_contain

_virama_combining_class = 9
_alabel_prefix = b"xn--"
_unicode_dots_re = re.compile("[\u002e\u3002\uff0e\uff61]")


class IDNAError(UnicodeError):
    """Base exception for all IDNA-encoding related problems"""

    pass


class IDNABidiError(IDNAError):
    """Exception when bidirectional requirements are not satisfied"""

    pass


class InvalidCodepoint(IDNAError):
    """Exception when a disallowed or unallocated codepoint is used"""

    pass


class InvalidCodepointContext(IDNAError):
    """Exception when the codepoint is not valid in the context it is used"""

    pass


def _combining_class(cp: int) -> int:
    v = unicodedata.combining(chr(cp))
    if v == 0:
        if not unicodedata.name(chr(cp)):
            raise ValueError("Unknown character in unicodedata")
    return v


def _is_script(cp: str, script: str) -> bool:
    return intranges_contain(ord(cp), idnadata.scripts[script])


def _punycode(s: str) -> bytes:
    return s.encode("punycode")


def _unot(s: int) -> str:
    return "U+{:04X}".format(s)


def valid_label_length(label: Union[bytes, str]) -> bool:
    """Check that a label does not exceed the maximum permitted length.

    Per :rfc:`1035` (and :rfc:`5891` §4.2.4) a DNS label must not exceed
    63 octets. The argument may be either a :class:`str` (a U-label, where
    length is measured in characters) or :class:`bytes` (an A-label, where
    length is measured in octets).

    :param label: The label to check.
    :returns: ``True`` if the label is within the length limit, otherwise
        ``False``.
    """
    if len(label) > 63:
        return False
    return True


def valid_string_length(label: Union[bytes, str], trailing_dot: bool) -> bool:
    """Check that a full domain name does not exceed the maximum length.

    Per :rfc:`1035`, a domain name is limited to 253 octets when no trailing
    dot is present, or 254 octets when one is included.

    :param label: The full (possibly multi-label) domain name.
    :param trailing_dot: ``True`` if ``label`` includes a trailing ``.``.
    :returns: ``True`` if the domain is within the length limit, otherwise
        ``False``.
    """
    if len(label) > (254 if trailing_dot else 253):
        return False
    return True


def check_bidi(label: str, check_ltr: bool = False) -> bool:
    """Validate the Bidi Rule from :rfc:`5893` for a single label.

    The Bidi Rule constrains how bidirectional characters (Hebrew, Arabic,
    etc.) may appear within a label. By default the check is only applied
    when the label contains at least one right-to-left character (Unicode
    bidirectional categories ``R``, ``AL``, or ``AN``); set ``check_ltr``
    to ``True`` to apply it to LTR-only labels as well.

    :param label: The label to validate, as a Unicode string.
    :param check_ltr: If ``True``, apply the rules even when the label
        contains no RTL characters.
    :returns: ``True`` if the label satisfies the Bidi Rule.
    :raises IDNABidiError: If any of Bidi Rule conditions 1-6 are violated,
        or if the directional category of a codepoint cannot be determined.
    """
    # Bidi rules should only be applied if string contains RTL characters
    bidi_label = False
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)
        if direction == "":
            # String likely comes from a newer version of Unicode
            raise IDNABidiError("Unknown directionality in label {} at position {}".format(repr(label), idx))
        if direction in ["R", "AL", "AN"]:
            bidi_label = True
    if not bidi_label and not check_ltr:
        return True

    # Bidi rule 1
    direction = unicodedata.bidirectional(label[0])
    if direction in ["R", "AL"]:
        rtl = True
    elif direction == "L":
        rtl = False
    else:
        raise IDNABidiError("First codepoint in label {} must be directionality L, R or AL".format(repr(label)))

    valid_ending = False
    number_type: Optional[str] = None
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)

        if rtl:
            # Bidi rule 2
            if direction not in [
                "R",
                "AL",
                "AN",
                "EN",
                "ES",
                "CS",
                "ET",
                "ON",
                "BN",
                "NSM",
            ]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a right-to-left label".format(idx))
            # Bidi rule 3
            if direction in ["R", "AL", "EN", "AN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False
            # Bidi rule 4
            if direction in ["AN", "EN"]:
                if not number_type:
                    number_type = direction
                else:
                    if number_type != direction:
                        raise IDNABidiError("Can not mix numeral types in a right-to-left label")
        else:
            # Bidi rule 5
            if direction not in ["L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a left-to-right label".format(idx))
            # Bidi rule 6
            if direction in ["L", "EN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

    if not valid_ending:
        raise IDNABidiError("Label ends with illegal codepoint directionality")

    return True


def check_initial_combiner(label: str) -> bool:
    """Reject labels that begin with a combining mark.

    Per :rfc:`5891` §4.2.3.2 a label must not start with a character of
    Unicode general category ``M`` (Mark).

    :param label: The label to check.
    :returns: ``True`` if the first character is not a combining mark.
    :raises IDNAError: If the label begins with a combining character.
    """
    if unicodedata.category(label[0])[0] == "M":
        raise IDNAError("Label begins with an illegal combining character")
    return True


def check_hyphen_ok(label: str) -> bool:
    """Validate the hyphen restrictions for a label.

    Per :rfc:`5891` §4.2.3.1 a label must not start or end with a hyphen
    (``U+002D``), and must not have hyphens in both the third and fourth
    positions (the prefix reserved for A-labels).

    :param label: The label to check.
    :returns: ``True`` if the hyphen restrictions are satisfied.
    :raises IDNAError: If any of the hyphen restrictions are violated.
    """
    if label[2:4] == "--":
        raise IDNAError("Label has disallowed hyphens in 3rd and 4th position")
    if label[0] == "-" or label[-1] == "-":
        raise IDNAError("Label must not start or end with a hyphen")
    return True


def check_nfc(label: str) -> None:
    """Require that a label is in Unicode Normalization Form C.

    :param label: The label to check.
    :raises IDNAError: If ``label`` differs from its NFC normalisation.
    """
    if unicodedata.normalize("NFC", label) != label:
        raise IDNAError("Label must be in Normalization Form C")


def valid_contextj(label: str, pos: int) -> bool:
    """Validate the CONTEXTJ rules from :rfc:`5892` Appendix A.

    These rules govern the contextual use of the joiner codepoints
    ``U+200C`` (ZERO WIDTH NON-JOINER, Appendix A.1) and ``U+200D``
    (ZERO WIDTH JOINER, Appendix A.2) within a label.

    :param label: The label containing the codepoint.
    :param pos: Index of the joiner codepoint within ``label``.
    :returns: ``True`` if the codepoint at ``pos`` satisfies its CONTEXTJ
        rule, ``False`` otherwise (including when the codepoint at
        ``pos`` is not a recognised joiner).
    :raises ValueError: If an adjacent codepoint has no Unicode name when
        determining its combining class.
    """
    cp_value = ord(label[pos])

    if cp_value == 0x200C:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True

        ok = False
        for i in range(pos - 1, -1, -1):
            joining_type = idnadata.joining_types().get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("L"), ord("D")]:
                ok = True
                break
            else:
                break

        if not ok:
            return False

        ok = False
        for i in range(pos + 1, len(label)):
            joining_type = idnadata.joining_types().get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("R"), ord("D")]:
                ok = True
                break
            else:
                break
        return ok

    if cp_value == 0x200D:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True
        return False

    else:
        return False


def valid_contexto(label: str, pos: int, exception: bool = False) -> bool:
    """Validate the CONTEXTO rules from :rfc:`5892` Appendix A.

    Covers the contextual rules for codepoints such as MIDDLE DOT
    (``U+00B7``), Greek lower numeral sign, Hebrew punctuation, Katakana
    middle dot, and the Arabic-Indic / Extended Arabic-Indic digit ranges.

    :param label: The label containing the codepoint.
    :param pos: Index of the codepoint within ``label``.
    :param exception: Reserved for forward compatibility; currently unused.
    :returns: ``True`` if the codepoint at ``pos`` satisfies its CONTEXTO
        rule, ``False`` otherwise (including when the codepoint is not a
        recognised CONTEXTO codepoint).
    """
    cp_value = ord(label[pos])

    if cp_value == 0x00B7:
        if 0 < pos < len(label) - 1:
            if ord(label[pos - 1]) == 0x006C and ord(label[pos + 1]) == 0x006C:
                return True
        return False

    elif cp_value == 0x0375:
        if pos < len(label) - 1 and len(label) > 1:
            return _is_script(label[pos + 1], "Greek")
        return False

    elif cp_value == 0x05F3 or cp_value == 0x05F4:
        if pos > 0:
            return _is_script(label[pos - 1], "Hebrew")
        return False

    elif cp_value == 0x30FB:
        for cp in label:
            if cp == "\u30fb":
                continue
            if _is_script(cp, "Hiragana") or _is_script(cp, "Katakana") or _is_script(cp, "Han"):
                return True
        return False

    elif 0x660 <= cp_value <= 0x669:
        for cp in label:
            if 0x6F0 <= ord(cp) <= 0x06F9:
                return False
        return True

    elif 0x6F0 <= cp_value <= 0x6F9:
        for cp in label:
            if 0x660 <= ord(cp) <= 0x0669:
                return False
        return True

    return False


def check_label(label: Union[str, bytes, bytearray]) -> None:
    """Run the full set of IDNA 2008 validity checks on a single label.

    Applies, in order: NFC normalisation (:func:`check_nfc`), hyphen
    restrictions (:func:`check_hyphen_ok`), the no-leading-combiner rule
    (:func:`check_initial_combiner`), per-codepoint validity (PVALID,
    CONTEXTJ, CONTEXTO classes from :rfc:`5892`), and the Bidi Rule
    (:func:`check_bidi`).

    :param label: The label to validate. ``bytes`` or ``bytearray`` input
        is decoded as UTF-8 first.
    :raises IDNAError: If the label is empty or fails a structural rule.
    :raises InvalidCodepoint: If the label contains a DISALLOWED or
        UNASSIGNED codepoint.
    :raises InvalidCodepointContext: If a CONTEXTJ or CONTEXTO codepoint
        is not valid in its context.
    :raises IDNABidiError: If the Bidi Rule is violated.
    """
    if isinstance(label, (bytes, bytearray)):
        label = label.decode("utf-8")
    if len(label) == 0:
        raise IDNAError("Empty Label")

    check_nfc(label)
    check_hyphen_ok(label)
    check_initial_combiner(label)

    for pos, cp in enumerate(label):
        cp_value = ord(cp)
        if intranges_contain(cp_value, idnadata.codepoint_classes["PVALID"]):
            continue
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTJ"]):
            try:
                if not valid_contextj(label, pos):
                    raise InvalidCodepointContext(
                        "Joiner {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                    )
            except ValueError:
                raise IDNAError(
                    "Unknown codepoint adjacent to joiner {} at position {} in {}".format(
                        _unot(cp_value), pos + 1, repr(label)
                    )
                )
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTO"]):
            if not valid_contexto(label, pos):
                raise InvalidCodepointContext(
                    "Codepoint {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                )
        else:
            raise InvalidCodepoint(
                "Codepoint {} at position {} of {} not allowed".format(_unot(cp_value), pos + 1, repr(label))
            )

    check_bidi(label)


def alabel(label: str) -> bytes:
    """Convert a single U-label into its A-label form.

    The result is the ASCII-Compatible Encoding (ACE) form per :rfc:`5891`
    §4: the label is validated, Punycode-encoded, and prefixed with
    ``xn--``. Pure ASCII labels that are already valid IDNA labels are
    returned unchanged (as :class:`bytes`).

    :param label: The label to convert, as a Unicode string.
    :returns: The A-label as ASCII-encoded :class:`bytes`.
    :raises IDNAError: If the label is invalid or the resulting A-label
        exceeds 63 octets.
    """
    try:
        label_bytes = label.encode("ascii")
        ulabel(label_bytes)
        if not valid_label_length(label_bytes):
            raise IDNAError("Label too long")
        return label_bytes
    except UnicodeEncodeError:
        pass

    check_label(label)
    label_bytes = _alabel_prefix + _punycode(label)

    if not valid_label_length(label_bytes):
        raise IDNAError("Label too long")

    return label_bytes


def ulabel(label: Union[str, bytes, bytearray]) -> str:
    """Convert a single A-label into its U-label form.

    Performs the inverse of :func:`alabel`: an ``xn--``-prefixed label is
    Punycode-decoded and validated. Labels that are already Unicode (or
    plain ASCII without the ACE prefix) are validated and returned as a
    Unicode string.

    :param label: The label to convert. ``bytes`` or ``bytearray`` input
        is treated as ASCII.
    :returns: The U-label as a Unicode string.
    :raises IDNAError: If the label is malformed or fails validation.
    """
    if not isinstance(label, (bytes, bytearray)):
        try:
            label_bytes = label.encode("ascii")
        except UnicodeEncodeError:
            check_label(label)
            return label
    else:
        label_bytes = bytes(label)

    label_bytes = label_bytes.lower()
    if label_bytes.startswith(_alabel_prefix):
        label_bytes = label_bytes[len(_alabel_prefix) :]
        if not label_bytes:
            raise IDNAError("Malformed A-label, no Punycode eligible content found")
        if label_bytes.decode("ascii")[-1] == "-":
            raise IDNAError("A-label must not end with a hyphen")
    else:
        check_label(label_bytes)
        return label_bytes.decode("ascii")

    try:
        label = label_bytes.decode("punycode")
    except UnicodeError:
        raise IDNAError("Invalid A-label")
    check_label(label)
    return label


def uts46_remap(domain: str, std3_rules: bool = True, transitional: bool = False) -> str:
    """Apply the UTS #46 character mapping to a domain string.

    Implements the mapping table from `UTS #46 §4
    <https://www.unicode.org/reports/tr46/>`_: each character is kept,
    replaced, or rejected based on its status (``V``, ``M``, ``D``, ``3``,
    ``I``). The result is returned in Normalisation Form C.

    :param domain: The full domain name to remap.
    :param std3_rules: If ``True``, apply the stricter STD3 ASCII rules
        (status ``3`` codepoints raise instead of being kept or mapped).
    :param transitional: If ``True``, use transitional processing (status
        ``D`` codepoints are mapped instead of kept). Transitional
        processing has been removed from UTS #46 and this option is
        retained only for backwards compatibility.
    :returns: The remapped domain, in Normalisation Form C.
    :raises InvalidCodepoint: If the domain contains a disallowed
        codepoint under the chosen rules.
    """
    from .uts46data import uts46data

    output = ""

    for pos, char in enumerate(domain):
        code_point = ord(char)
        uts46row = uts46data[code_point if code_point < 256 else bisect.bisect_left(uts46data, (code_point, "Z")) - 1]
        status = uts46row[1]
        replacement: Optional[str] = None
        if len(uts46row) == 3:
            replacement = uts46row[2]  # ty: ignore[index-out-of-bounds]
        if status == "V" or (status == "D" and not transitional) or (status == "3" and not std3_rules and replacement is None):
            output += char
        elif replacement is not None and (
            status == "M" or (status == "3" and not std3_rules) or (status == "D" and transitional)
        ):
            output += replacement
        elif status == "I":
            continue
        else:
            raise InvalidCodepoint(
                "Codepoint {} not allowed at position {} in {}".format(_unot(code_point), pos + 1, repr(domain))
            )

    return unicodedata.normalize("NFC", output)


def encode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    transitional: bool = False,
) -> bytes:
    """Encode a Unicode domain name into its ASCII (A-label) form.

    Splits the input on label separators (only ``U+002E`` if ``strict`` is
    set; otherwise also IDEOGRAPHIC FULL STOP ``U+3002``, FULLWIDTH FULL
    STOP ``U+FF0E``, and HALFWIDTH IDEOGRAPHIC FULL STOP ``U+FF61``),
    encodes each label with :func:`alabel`, and rejoins them with ``.``.
    Optionally pre-processes the input through :func:`uts46_remap`.

    :param s: The domain name to encode.
    :param strict: If ``True``, only ``U+002E`` is recognised as a label
        separator.
    :param uts46: If ``True``, apply UTS #46 mapping before encoding.
    :param std3_rules: Forwarded to :func:`uts46_remap` when ``uts46`` is
        ``True``.
    :param transitional: Forwarded to :func:`uts46_remap` when ``uts46``
        is ``True``. Deprecated: emits a :class:`DeprecationWarning` and
        will be removed in a future version.
    :returns: The encoded domain as ASCII :class:`bytes`.
    :raises IDNAError: If the domain is empty, contains an invalid label,
        or exceeds the maximum domain length.
    """
    if transitional:
        warnings.warn(
            "Transitional processing has been removed from UTS #46. "
            "The transitional argument will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except (UnicodeDecodeError, TypeError):
            raise IDNAError("should pass a unicode string to the function rather than a byte string.")
    if uts46:
        s = uts46_remap(s, std3_rules, transitional)

    # Reject inputs that exceed the maximum DNS domain length up-front
    # to avoid expensive computation on long inputs.
    if not valid_string_length(s, trailing_dot=True):
        raise IDNAError("Domain too long")

    trailing_dot = False
    result = []
    if strict:
        labels = s.split(".")
    else:
        labels = _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if labels[-1] == "":
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = alabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append(b"")
    s = b".".join(result)
    if not valid_string_length(s, trailing_dot):
        raise IDNAError("Domain too long")
    return s


def decode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
) -> str:
    """Decode an A-label-encoded domain name back to Unicode.

    Splits the input on label separators (see :func:`encode` for the
    rules), decodes each label with :func:`ulabel`, and rejoins them
    with ``.``. Optionally pre-processes the input through
    :func:`uts46_remap`.

    :param s: The domain name to decode.
    :param strict: If ``True``, only ``U+002E`` is recognised as a label
        separator.
    :param uts46: If ``True``, apply UTS #46 mapping before decoding.
    :param std3_rules: Forwarded to :func:`uts46_remap` when ``uts46`` is
        ``True``.
    :returns: The decoded domain as a Unicode string.
    :raises IDNAError: If the input is not valid ASCII, contains an
        invalid label, or is empty.
    """
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except (UnicodeDecodeError, TypeError):
            raise IDNAError("Invalid ASCII in A-label")
    if uts46:
        s = uts46_remap(s, std3_rules, False)
    # Reject inputs that exceed the maximum DNS domain length up-front
    # to avoid expensive computation on long inputs.
    if not valid_string_length(s, trailing_dot=True):
        raise IDNAError("Domain too long")
    trailing_dot = False
    result = []
    if not strict:
        labels = _unicode_dots_re.split(s)
    else:
        labels = s.split(".")
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if not labels[-1]:
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = ulabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append("")
    return ".".join(result)
