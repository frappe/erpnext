# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.edi.doctype.code_list.code_list import (
	_version_key,
	get_codes_for,
	get_default_code,
	get_docnames_for,
	resolve_code_list,
)

CANONICAL_URI = "urn:test:erpnext:codeliste:resolve"
OLD_VERSION = f"{CANONICAL_URI}:3"
NEW_VERSION = f"{CANONICAL_URI}:10"
UNKNOWN_URI = "urn:test:erpnext:codeliste:missing"


class TestCodeList(FrappeTestCase):
	def setUp(self):
		"""Create two versions of one code list. FrappeTestCase rolls back once per class, so the inserts are guarded."""
		for name, version in ((OLD_VERSION, "3"), (NEW_VERSION, "10")):
			if not frappe.db.exists("Code List", name):
				frappe.get_doc(
					doctype="Code List",
					name=name,
					title=name,
					canonical_uri=CANONICAL_URI,
					version=version,
				).insert()

		default_code = frappe.get_doc(
			doctype="Common Code",
			title="Test Default",
			common_code="XYZ",
			code_list=NEW_VERSION,
		).insert()
		frappe.db.set_value("Code List", NEW_VERSION, "default_common_code", default_code.name)

		# resolution is request-cached, so fixtures must not be masked by earlier lookups
		frappe.local.request_cache.clear()

	def test_version_key_orders_integers_and_iso_dates(self):
		"""Integer and ISO date versions must both order correctly, unlike a lexical sort."""
		self.assertEqual(sorted(["10", "3", None, "9"], key=_version_key), [None, "3", "9", "10"])
		self.assertEqual(
			sorted(["2020-11-05", "2019-12-31", "2020-01-01"], key=_version_key),
			["2019-12-31", "2020-01-01", "2020-11-05"],
		)

	def test_canonical_uri_resolves_to_latest_version(self):
		self.assertEqual(resolve_code_list(CANONICAL_URI), NEW_VERSION)

	def test_name_resolves_to_itself(self):
		"""Passing a version-specific name must return that version, not the latest one."""
		self.assertEqual(resolve_code_list(OLD_VERSION), OLD_VERSION)

	def test_name_takes_precedence_over_canonical_uri(self):
		"""A document named like a canonical URI must not redirect to another version."""
		frappe.get_doc(
			doctype="Code List",
			name=CANONICAL_URI,
			title=CANONICAL_URI,
			canonical_uri=CANONICAL_URI,
			version="1",
		).insert()
		frappe.local.request_cache.clear()

		self.assertEqual(resolve_code_list(CANONICAL_URI), CANONICAL_URI)

	def test_unknown_uri_resolves_to_none(self):
		self.assertIsNone(resolve_code_list(UNKNOWN_URI))

	def test_lookups_are_empty_for_unknown_code_list(self):
		"""An unresolved code list must not fall through to an unfiltered query."""
		self.assertEqual(get_codes_for(UNKNOWN_URI, "UOM", "Nos"), ())
		self.assertEqual(get_docnames_for(UNKNOWN_URI, "UOM", "XYZ"), ())
		self.assertIsNone(get_default_code(UNKNOWN_URI))

	def test_default_code_follows_latest_version(self):
		self.assertEqual(get_default_code(CANONICAL_URI), "XYZ")
