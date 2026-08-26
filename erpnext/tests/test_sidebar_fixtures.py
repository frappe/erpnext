# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""erpnext ships its navigation as `Sidebar` fixtures, one per module that has an arrangement.

The framework renamed `Module Sidebar` to `Sidebar` and moved an app's fixtures from
`<module>/module_sidebar/` to `<module>/sidebar/`. An app that has not followed is not broken --
its folder is simply never walked, and each of its modules falls back to a base computed from its
own contents -- so nothing here fails loudly if the conversion is half done. That is exactly why
it is asserted: the failure mode is erpnext's curated navigation quietly reverting to generated.

Two facts, and they are different questions:

- `TestTheFixturesAreWhereMigrateLooks` is about the *files*. Import finds them, and orphan
  removal derives the same record name from the path that the file declares -- a mismatch there
  makes migrate delete the very rows it just imported.
- `TestTheModulesResolveToTheirShippedArrangement` is about *navigation*, asked through the
  resolver seam rather than through any payload key. It is what says the files actually took.
"""

import json
import os

import frappe
from frappe.desk.doctype.sidebar.convert_fixtures import export_path
from frappe.desk.doctype.sidebar.sidebar import resolve_sidebar
from frappe.model.sync import create_entity_file_map, get_doc_files

from erpnext.tests.utils import ERPNextTestSuite

#: Every module that ships a `Sidebar`. `Banking` is deliberately absent -- it is new, has no
#: arrangement yet, and a module with no fixture is not baseless: it is served by a computed base
#: built from its own contents.
#:
#: Eleven of these are real arrangements, and ten are not, and the difference is worth knowing
#: before reading a failure. `Accounts` (124 items), `Selling` (62), `Stock` (56) and the rest of
#: the large modules carry navigation somebody arranged. The ten small ones -- `Bulk Transaction`,
#: `Communication`, `EDI`, `ERPNext Integrations`, `Maintenance`, `Portal`, `Regional`,
#: `Subcontracting`, `Telephony`, `Utilities` -- are a computed base that was materialized and
#: frozen, legible in the rows: `icon: settings` on exactly the doctypes with "settings" in the
#: name, and the `Reports` section label as a code constant out of `generate_items`.
#:
#: For those ten the header icon is the only authored part, which makes it the assertion that
#: separates shipped from computed for every module here: `build_computed_base` hands out
#: `hammer`, and not one of these twenty-one says `hammer`.
SIDEBAR_MODULES = [
	"Accounts",
	"Assets",
	"Bulk Transaction",
	"Buying",
	"CRM",
	"Communication",
	"EDI",
	"ERPNext Integrations",
	"Maintenance",
	"Manufacturing",
	"Portal",
	"Projects",
	"Quality Management",
	"Regional",
	"Selling",
	"Setup",
	"Stock",
	"Subcontracting",
	"Support",
	"Telephony",
	"Utilities",
]

#: `Portal` ships a fixture with an empty item list, so it has no arrangement to resolve to.
#: `get_sidebar_bases` fills an empty document's rows from the computed base and keeps only what
#: the document says about *itself* -- title, icon, app -- so every resolution fact below would be
#: a fact about the framework's fallback rather than about erpnext's authoring. It is named here,
#: not filtered out by a rule, so that a fixture which lost its items has to be excluded by hand.
MODULES_WITH_SHIPPED_ITEMS = [module for module in SIDEBAR_MODULES if module != "Portal"]


def shipped(module: str) -> dict:
	"""The fixture as it sits in the app folder, before any site has seen it."""
	with open(export_path(module)) as f:
		return json.load(f)


class TestTheFixturesAreWhereMigrateLooks(ERPNextTestSuite):
	def test_every_authoring_module_ships_one(self):
		"""Named individually rather than globbed: a fixture that stopped being exported would
		pass a test that only checks the files it can find."""
		for module in SIDEBAR_MODULES:
			with self.subTest(module=module):
				self.assertTrue(os.path.exists(export_path(module)))

	def test_they_declare_the_renamed_doctype(self):
		"""A fixture still naming `Module Sidebar` would import against a doctype the site no
		longer has -- which is why the walk skips the old folder rather than failing on it."""
		for module in SIDEBAR_MODULES:
			with self.subTest(module=module):
				self.assertEqual(shipped(module)["doctype"], "Sidebar")

	def test_the_module_walk_picks_them_up(self):
		"""`get_doc_files` is what migrate imports from. It only opens folders named by
		`IMPORTABLE_DOCTYPES`, so this is the fact that the folder rename landed."""
		for module in SIDEBAR_MODULES:
			with self.subTest(module=module):
				module_path = frappe.get_module_path(module)
				self.assertIn(export_path(module), get_doc_files(files=[], start_path=module_path))

	def test_record_name_and_filename_agree(self):
		"""Orphan removal maps a file to a record by reading the `name` out of it and looking for
		that record. Standard rows whose file it cannot find are deleted, so a fixture whose name
		and path disagree is imported and then reaped on the same migrate."""
		known = create_entity_file_map(["Sidebar"])["Sidebar"]

		for module in SIDEBAR_MODULES:
			with self.subTest(module=module):
				self.assertEqual(shipped(module)["name"], module)
				self.assertEqual(known.get(module), export_path(module))

	def test_they_store_no_item_key(self):
		"""A base row's identity is derived from its own columns, so `Sidebar.clear_stored_keys`
		nulls `key` on the way in and `no_nulls=True` drops it on the way back out. A fixture
		still carrying one disagrees with what a developer-mode re-export would write, which is
		how a diff nobody authored appears -- and frappe's own eleven shipped fixtures carry none.

		Only `key`. A Check field valued `0` is not null, so `is_default_module` does survive an
		export and every one of frappe's fixtures ships it; dropping it here would be the same
		divergence in the other direction."""
		for module in SIDEBAR_MODULES:
			with self.subTest(module=module):
				for item in shipped(module)["items"]:
					self.assertNotIn("key", item)

	def test_portal_ships_no_arrangement_of_its_own(self):
		"""Named rather than left implicit, because it is why `Portal` is absent from every
		resolution fact below. An empty document is not a hidden module: `get_sidebar_bases` fills
		its rows from the computed base and keeps only what it says about itself, so what this
		fixture contributes is its icon."""
		self.assertEqual(shipped("Portal")["items"], [])
		self.assertTrue(shipped("Portal")["header_icon"])
		self.assertNotIn("Portal", MODULES_WITH_SHIPPED_ITEMS)


class TestTheModulesResolveToTheirShippedArrangement(ERPNextTestSuite):
	"""The point of the whole exercise: what a person's navigation resolves to.

	Asserted as Administrator, who is filtered out of nothing and carries no customization, so the
	resolution is the shipped arrangement itself rather than one reader's view of it. That a
	*restricted* reader sees less is the framework's fact and is asserted there.
	"""

	def test_a_module_resolves_to_the_items_its_fixture_ships(self):
		"""Labels in order, which is the whole of what the fixture authored. A computed base would
		still resolve to something -- these modules have doctypes -- so "resolves to anything at
		all" is not the fact worth asserting."""
		for module in MODULES_WITH_SHIPPED_ITEMS:
			with self.subTest(module=module):
				resolved = resolve_sidebar(module, "Administrator")

				self.assertIsNotNone(resolved)
				self.assertEqual(
					[item["label"] for item in resolved.items],
					[item["label"] for item in shipped(module)["items"]],
				)

	def test_the_label_and_icon_are_the_fixture_s(self):
		"""`resolve_sidebar` answers `None` for a scope that resolves to nothing, and that is the
		failure this file exists to catch -- so it is asserted against rather than skipped over.
		Ten fixtures failing to import would otherwise pass this test in silence."""
		for module in MODULES_WITH_SHIPPED_ITEMS:
			with self.subTest(module=module):
				resolved = resolve_sidebar(module, "Administrator")
				self.assertIsNotNone(resolved)

				fixture = shipped(module)
				self.assertEqual(resolved.label, fixture["title"])
				self.assertEqual(resolved.header_icon, fixture["header_icon"])

	def test_a_module_opens_on_its_own_navigation(self):
		"""Landing is derived from the resolved entries, so a module falling back to a computed
		base would land somewhere the fixture never named."""
		for module in MODULES_WITH_SHIPPED_ITEMS:
			with self.subTest(module=module):
				resolved = resolve_sidebar(module, "Administrator")

				self.assertIsNotNone(resolved)
				self.assertIsNotNone(resolved.landing)
