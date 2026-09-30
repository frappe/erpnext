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
