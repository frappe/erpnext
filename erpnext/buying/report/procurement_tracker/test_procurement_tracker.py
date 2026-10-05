# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.utils import add_days, getdate, nowdate

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.mapper import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import (
	make_material_request,
	make_material_request_for_items,
)
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_invoice_from_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestProcurementTracker(ERPNextTestSuite):
	def run_report(self, **filters):
		return execute({"company": "_Test Company", **filters})[1]

	def test_report_executes_and_lists_po(self):
		po = create_purchase_order(company="_Test Company")

		self.assertIn(po.name, {row.get("purchase_order") for row in self.run_report()})

	def make_priced_request(self):
		mr = make_material_request(do_not_submit=True)
		mr.items[0].update({"rate": 90, "amount": 900})
		mr.submit()
		return mr

	def test_request_item_ordered_on_two_lines_is_estimated_once(self):
		mr = self.make_priced_request()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].qty = 4
		po.append("items", {**po.items[0].as_dict(no_default_fields=True), "qty": 6})
		with self.change_settings("Buying Settings", {"allow_multiple_items": 1}):
			po.submit()

		rows = [row for row in self.run_report() if row.get("purchase_order") == po.name]
		self.assertCountEqual([row["estimated_cost"] for row in rows], [360, 540])
		self.assertEqual(sum(row["estimated_cost"] for row in rows), mr.items[0].amount)

	def test_filtered_out_order_keeps_its_share_of_the_estimate(self):
		mr = self.make_priced_request()
		for qty, transaction_date in ((4, add_days(nowdate(), -1)), (6, nowdate())):
			po = make_purchase_order(mr.name)
			po.update({"supplier": "_Test Supplier", "transaction_date": transaction_date})
			po.items[0].qty = qty
			po.submit()

		data = self.run_report(from_date=nowdate(), to_date=nowdate())
		rows = [row for row in data if row.get("material_request_no") == mr.name]
		self.assertEqual([(row["purchase_order"], row["estimated_cost"]) for row in rows], [(po.name, 540)])

	def test_each_po_line_is_a_row(self):
		second_item = make_item("_Test Procurement Tracker Item", {"is_stock_item": 1}).name
		po = create_purchase_order(do_not_submit=True)
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
		po.submit()

		rows = [row for row in self.run_report() if row.get("purchase_order") == po.name]
		self.assertCountEqual(
			[(row["item_code"], row["quantity"]) for row in rows],
			[(item.item_code, item.qty) for item in po.items],
		)

	def test_actual_cost_adds_up_every_invoice(self):
		po = create_purchase_order(qty=10, rate=90)
		for qty in (4, 3):
			invoice = make_purchase_invoice(po.name)
			invoice.items[0].qty = qty
			invoice.submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_cost"], 630)

	def test_unordered_rows_of_a_partly_ordered_request_are_listed(self):
		mr = make_material_request_for_items(["_Test Item", "_Test Item Home Desktop 100"])
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items = po.items[:1]
		po.submit()

		rows = [row for row in self.run_report() if row.get("material_request_no") == mr.name]
		self.assertCountEqual(
			[(row["item_code"], row.get("purchase_order")) for row in rows],
			[("_Test Item", po.name), ("_Test Item Home Desktop 100", None)],
		)

	def test_billed_receipt_keeps_actual_delivery_date(self):
		po = create_purchase_order(qty=10)
		receipt = create_pr_against_po(po.name, received_qty=5)
		make_invoice_from_receipt(receipt.name).submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_delivery_date"], getdate(receipt.posting_date))
