# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.item_where_used.item_where_used import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWhereUsed(ERPNextTestSuite):
	"""Correctness tests for the Item Where Used report."""

	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def test_item_used_in_bom_listed(self):
		raw_material = "_Test Item"
		finished_good = "_Test FG Item"

		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": finished_good,
				"company": "_Test Company",
				"currency": "INR",
				"quantity": 1,
				"items": [{"item_code": raw_material, "qty": 1}],
			}
		)
		bom.insert()
		bom.submit()

		rows = self.run_report(item=raw_material)
		matching = [row for row in rows if row.document_name == bom.name]

		self.assertTrue(matching, f"BOM {bom.name} not found in report rows for {raw_material}")
		row = matching[0]
		self.assertEqual(row.section, "Where Used")
		self.assertEqual(row.reference_type, "BOM Component")
		self.assertEqual(row.document_type, "BOM")
		self.assertEqual(row.related_item, finished_good)
		self.assertEqual(row.quantity, 1)

	def test_bom_rows_require_read_permission(self):
		bom = self.make_bom()
		user = self.make_report_user("Item Manager")
		with self.set_user(user):
			self.assertFalse(frappe.has_permission("BOM", "read"))
			for item, section in (("_Test Item", "Where Used"), (bom.item, "References")):
				rows = self.run_report(item=item, section=section)
				self.assertFalse(any(row.document_type == "BOM" for row in rows))

	def test_bom_user_permission_filters_both_sections(self):
		allowed_bom = self.make_bom()
		restricted_bom = self.make_bom()
		user = self.make_report_user("Manufacturing User")
		self.allow_document(user, "BOM", allowed_bom.name)

		with self.set_user(user):
			self.assertTrue(frappe.has_permission("BOM", "read"))
			for item, section in (("_Test Item", "Where Used"), (allowed_bom.item, "References")):
				rows = self.run_report(item=item, section=section)
				names = {row.document_name for row in rows if row.document_type == "BOM"}
				self.assertIn(allowed_bom.name, names)
				self.assertNotIn(restricted_bom.name, names)

	def test_selected_item_permission_without_filter_metadata(self):
		user = self.make_report_user("Item Manager")
		self.allow_document(user, "Item", "_Test Item")

		with self.set_user(user):
			self.run_report(item="_Test Item")
			with self.assertRaises(frappe.PermissionError):
				execute({"item": "_Test FG Item"})

	def make_bom(self):
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": "_Test FG Item",
				"company": "_Test Company",
				"currency": "INR",
				"quantity": 1,
				"items": [{"item_code": "_Test Item", "qty": 1}],
			}
		).insert()
		return bom.submit()

	def make_report_user(self, role):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "test_item_where_used_permissions@example.com",
				"first_name": "Item Usage",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert()
		return user.name

	def allow_document(self, user, doctype, name):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": doctype,
				"for_value": name,
				"apply_to_all_doctypes": 1,
			}
		).insert()
