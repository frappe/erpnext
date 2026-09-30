# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.utils import add_days, flt, nowdate

from erpnext.tests.utils import ERPNextTestSuite


class TestProcurementTracker(ERPNextTestSuite):
	def test_report_executes_and_lists_po(self):
		# get_po_entries returns one representative line per (Purchase Order, material_request_item);
		# this exercises that query so the report stays valid on Postgres.
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.procurement_tracker.procurement_tracker import execute

		po = create_purchase_order(company="_Test Company")

		columns, data = execute({"company": "_Test Company"})

		self.assertTrue(columns)
		self.assertIn(po.name, {row.get("purchase_order") for row in data})

	def test_multi_line_po_stays_one_coherent_row(self):
		# Lines sharing the same (blank) material_request_item collapse to ONE row, matching the
		# pre-effort MariaDB row count — and that row must be a real PO line, not a per-column
		# Max() chimera mixing one line's item_code with another line's qty/amount.
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

		real_lines = {(d.item_code, flt(d.qty), flt(d.amount)) for d in po.items}
		row = po_rows[0]
		self.assertIn(
			(row.get("item_code"), flt(row.get("quantity")), flt(row.get("purchase_order_amt"))),
			real_lines,
		)
