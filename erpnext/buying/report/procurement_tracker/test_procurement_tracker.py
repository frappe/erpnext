# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from erpnext.tests.utils import ERPNextTestSuite


class TestProcurementTracker(ERPNextTestSuite):
	def test_report_executes_and_lists_po(self):
		# get_po_entries groups by (Purchase Order, material_request_item, Purchase Order Item)
		# while selecting other child columns; this exercises that GROUP BY so the report stays
		# valid on Postgres (which rejects selecting non-grouped columns).
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.procurement_tracker.procurement_tracker import execute

		po = create_purchase_order(company="_Test Company")

		columns, data = execute({"company": "_Test Company"})

		self.assertTrue(columns)
		self.assertIn(po.name, {row.get("purchase_order") for row in data})
