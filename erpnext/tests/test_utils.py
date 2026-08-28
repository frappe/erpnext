# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.tests.utils import (
	BootstrapTestData,
	ERPNextTestSuite,
	change_settings,
	if_lending_app_installed,
	if_lending_app_not_installed,
)


class TestERPNextTestUtils(ERPNextTestSuite):
	def test_make_records_reuses_item_price_when_rate_changes(self):
		fixture = BootstrapTestData.__new__(BootstrapTestData)
		filters = {"item_code": "_Test Item", "price_list": "_Test Price List Rest of the World"}
		item_price = frappe.db.get_value("Item Price", filters, "name")
		self.assertIsNotNone(item_price)
		frappe.db.set_value("Item Price", item_price, "price_list_rate", 999)

		fixture.make_item_price()

		self.assertEqual(frappe.db.count("Item Price", filters), 1)
		self.assertEqual(frappe.db.get_value("Item Price", filters, "price_list_rate"), 10)

	def test_make_custom_doctype_repairs_each_missing_doctype(self):
		fixture = BootstrapTestData.__new__(BootstrapTestData)
		existing_doctypes = {"Shelf", "Rack", "Pallet", "Inv Site"}

		with (
			patch.object(
				frappe.db,
				"exists",
				side_effect=lambda doctype, name: doctype == "DocType" and name in existing_doctypes,
			),
			patch("erpnext.tests.utils.frappe.get_doc") as get_doc,
		):
			fixture.make_custom_doctype()

		created_doctypes = [call.args[0]["name"] for call in get_doc.call_args_list]
		self.assertCountEqual(created_doctypes, ["Store", "Order Assignment"])

	def test_change_settings_restores_values_after_error(self):
		original = frappe.db.get_single_value("Stock Settings", "auto_indent")
		changed = 0 if original else 1

		with self.assertRaisesRegex(RuntimeError, "expected failure"):
			with change_settings("Stock Settings", auto_indent=changed):
				self.assertEqual(frappe.db.get_single_value("Stock Settings", "auto_indent"), changed)
				raise RuntimeError("expected failure")

		self.assertEqual(frappe.db.get_single_value("Stock Settings", "auto_indent"), original)

	def test_lending_decorators_preserve_names_and_skip(self):
		with patch("erpnext.tests.utils.frappe.get_installed_apps", return_value=[]):

			@if_lending_app_installed
			def requires_lending():
				return True

			@if_lending_app_not_installed
			def excludes_lending():
				return True

			self.assertEqual(requires_lending.__name__, "requires_lending")
			self.assertEqual(excludes_lending.__name__, "excludes_lending")
			with self.assertRaises(unittest.SkipTest):
				requires_lending()
			self.assertTrue(excludes_lending())

		with patch("erpnext.tests.utils.frappe.get_installed_apps", return_value=["lending"]):

			@if_lending_app_installed
			def requires_lending():
				return True

			@if_lending_app_not_installed
			def excludes_lending():
				return True

			self.assertTrue(requires_lending())
			with self.assertRaises(unittest.SkipTest):
				excludes_lending()
