# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.report.item_where_used.item_where_used import execute
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWhereUsed(ERPNextTestSuite):
	"""Correctness tests for the Item Where Used report."""

	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def make_bom(self, item="_Test FG Item", raw_material="_Test Item"):
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": item,
				"company": "_Test Company",
				"currency": "INR",
				"quantity": 1,
				"items": [{"item_code": raw_material, "qty": 1}],
			}
		)
		bom.insert()
		bom.submit()
		return bom

	def get_bom_names(self, **filters):
		return {row.document_name for row in self.run_report(**filters) if row.document_type == "BOM"}

	def test_item_used_in_bom_listed(self):
		raw_material = "_Test Item"
		finished_good = "_Test FG Item"

		bom = self.make_bom(finished_good, raw_material)

		rows = self.run_report(item=raw_material)
		matching = [row for row in rows if row.document_name == bom.name]

		self.assertTrue(matching, f"BOM {bom.name} not found in report rows for {raw_material}")
		row = matching[0]
		self.assertEqual(row.section, "Where Used")
		self.assertEqual(row.reference_type, "BOM Component")
		self.assertEqual(row.document_type, "BOM")
		self.assertEqual(row.related_item, finished_good)
		self.assertEqual(row.quantity, 1)

	def test_bom_rows_need_bom_read_permission(self):
		bom = self.make_bom()
		user = make_fenced_user("where-used-item-manager@example.com", ["Item Manager"])

		with as_user(user):
			self.assertNotIn(bom.name, self.get_bom_names(item="_Test Item", section="Where Used"))
			self.assertNotIn(bom.name, self.get_bom_names(item=bom.item, section="References"))

	def test_bom_rows_respect_user_permissions(self):
		allowed_bom = self.make_bom()
		restricted_bom = self.make_bom()
		user = make_fenced_user(
			"where-used-stock-user@example.com", ["Stock User"], [("BOM", allowed_bom.name)]
		)

		with as_user(user):
			for filters in ({"item": "_Test Item", "section": "Where Used"}, {"item": allowed_bom.item}):
				bom_names = self.get_bom_names(**filters)
				self.assertIn(allowed_bom.name, bom_names)
				self.assertNotIn(restricted_bom.name, bom_names)

	def test_restricted_item_is_refused(self):
		user = make_fenced_user("where-used-item-user@example.com", ["Stock User"], [("Item", "_Test Item")])

		with as_user(user):
			self.run_report(item="_Test Item")
			self.assertRaises(frappe.PermissionError, self.run_report, item="_Test FG Item")
