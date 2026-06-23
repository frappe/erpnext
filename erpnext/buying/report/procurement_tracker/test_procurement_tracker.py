# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite


class TestProcurementTracker(ERPNextTestSuite):
	def test_report_executes_and_lists_po(self):
		# get_po_entries groups by (Purchase Order, material_request_item) and Max()-aggregates the
		# other child columns; this exercises that GROUP BY so the report stays valid on Postgres
		# (which rejects selecting non-grouped columns).
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.procurement_tracker.procurement_tracker import execute

		po = create_purchase_order(company="_Test Company")

		columns, data = execute({"company": "_Test Company"})

		self.assertTrue(columns)
		self.assertIn(po.name, {row.get("purchase_order") for row in data})

	def test_multi_line_po_stays_one_row(self):
		# A PO can carry several lines that share the same (blank) material_request_item. get_po_entries
		# groups by (Purchase Order, material_request_item) and Max()-aggregates the rest, so such a PO
		# yields ONE row — matching the pre-effort MariaDB output. Adding the Purchase Order Item PK to
		# the GROUP BY (the regression) splits it into one row per line, changing the MariaDB row count.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
		from erpnext.stock.doctype.item.test_item import make_item

		second_item = make_item("_Test Procurement Tracker Item", {"is_stock_item": 1}).name
		po = create_purchase_order(company="_Test Company", do_not_submit=True)
		po.append(
			"items",
			{
				"item_code": second_item,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 5,
				"rate": 100,
				"schedule_date": add_days(nowdate(), 1),
			},
		)
		po.save()
		po.submit()

		columns, data = execute({"company": "_Test Company"})

		po_rows = [row for row in data if row.get("purchase_order") == po.name]
		self.assertEqual(len(po_rows), 1)
