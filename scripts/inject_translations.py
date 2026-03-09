#!/usr/bin/env python3
"""
Inject translations into PO files.
Reads a PO file and fills in msgstr for known translations.
"""

import re
import sys
import os

# Import translation dictionaries
sys.path.insert(0, os.path.dirname(__file__))
from generate_translations import KURDISH_TRANSLATIONS, ARABIC_TRANSLATIONS


def inject_translations(po_path, translations):
    """Read a PO file and inject translations for matching msgids."""
    with open(po_path, "r", encoding="utf-8") as f:
        content = f.read()

    filled = 0
    already = 0

    # Process each msgid/msgstr block
    # We need to handle both single-line and multi-line msgid/msgstr

    lines = content.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect msgid line
        if line.startswith("msgid "):
            # Collect full msgid
            msgid_parts = []
            # Extract from first line: msgid "text"
            m = re.match(r'^msgid "(.*)"$', line)
            if m:
                msgid_parts.append(m.group(1))
            result.append(line)
            i += 1

            # Continuation lines for msgid (start with ")
            while i < len(lines) and lines[i].startswith('"'):
                m = re.match(r'^"(.*)"$', lines[i])
                if m:
                    msgid_parts.append(m.group(1))
                result.append(lines[i])
                i += 1

            full_msgid = "".join(msgid_parts)

            # Now we should be at msgstr line
            if i < len(lines) and lines[i].startswith("msgstr "):
                m = re.match(r'^msgstr "(.*)"$', lines[i])
                msgstr_val = m.group(1) if m else ""

                # Collect continuation lines
                msgstr_extra = []
                j = i + 1
                while j < len(lines) and lines[j].startswith('"'):
                    m2 = re.match(r'^"(.*)"$', lines[j])
                    if m2:
                        msgstr_val += m2.group(1)
                    msgstr_extra.append(lines[j])
                    j += 1

                # If msgstr is empty and we have a translation
                if msgstr_val == "" and full_msgid in translations and full_msgid != "":
                    trans = translations[full_msgid]
                    # Escape quotes in translation
                    trans = trans.replace('"', '\\"')
                    result.append(f'msgstr "{trans}"')
                    filled += 1
                    i = j  # Skip old msgstr + continuation lines
                else:
                    if msgstr_val != "" and full_msgid in translations:
                        already += 1
                    result.append(lines[i])
                    result.extend(msgstr_extra)
                    i = j
            continue

        result.append(line)
        i += 1

    with open(po_path, "w", encoding="utf-8") as f:
        f.write("\n".join(result))

    return filled, already


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locale_dir = os.path.join(base_dir, "erpnext", "locale")

    print("=" * 60)
    print("ZirakERP Translation Injector")
    print("=" * 60)

    # Kurdish
    ku_path = os.path.join(locale_dir, "ku.po")
    if os.path.exists(ku_path):
        print(f"\n[1/2] Injecting Kurdish translations into {ku_path}...")
        filled, already = inject_translations(ku_path, KURDISH_TRANSLATIONS)
        print(f"  ✓ Filled: {filled} strings")
        print(f"  ℹ Already translated: {already} strings")
    else:
        print(f"  ✗ Kurdish PO file not found: {ku_path}")

    # Arabic
    ar_path = os.path.join(locale_dir, "ar.po")
    if os.path.exists(ar_path):
        print(f"\n[2/2] Injecting Arabic translations into {ar_path}...")
        filled, already = inject_translations(ar_path, ARABIC_TRANSLATIONS)
        print(f"  ✓ Filled: {filled} strings")
        print(f"  ℹ Already translated: {already} strings")
    else:
        print(f"  ✗ Arabic PO file not found: {ar_path}")

    print("\n" + "=" * 60)
    print("Done! Translation injection complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
