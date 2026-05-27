#!/usr/bin/env python3
"""Overlay develop's .po translations onto hotfix's .po files.

Called by sync_hotfix_translations.sh before `bench update-po-files`.
Merge rules:
  a. msgid absent from develop  → keep hotfix's existing msgstr
  b. language not yet in hotfix → copy file as-is (bench will filter to main.pot)
  c. msgid present in both      → use develop's msgstr
"""
import shutil
from pathlib import Path

from babel.messages.pofile import read_po, write_po

DEVELOP = Path("/tmp/develop-po/erpnext/locale/")
LOCALE  = Path("./apps/erpnext/erpnext/locale/")

added = updated = 0

for src in sorted(DEVELOP.glob("*.po")):
    dst = LOCALE / src.name

    with src.open("rb") as f:
        dev = read_po(f)

    if not dst.exists():
        shutil.copy(src, dst)
        added += 1
        print(f"  [new]     {src.name}")
        continue

    with dst.open("rb") as f:
        hf = read_po(f)

    changes = 0
    for msg in hf:
        if msg.id and msg.id in dev and dev[msg.id].string and dev[msg.id].string != msg.string:
            msg.string = dev[msg.id].string
            changes += 1

    if changes:
        with dst.open("wb") as f:
            write_po(f, hf)
        updated += 1
        print(f"  [updated] {src.name} ({changes} msgstr(s) from develop)")
    else:
        print(f"  [no-op]   {src.name}")

print(f"\n{added} new language(s), {updated} updated.")
