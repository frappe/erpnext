# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.report.item_wise_purchase_history.item_wise_purchase_history import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWisePurchaseHistory(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				**extra,
			}
		)
		return execute(filters)

	def po_row(self, po_name, **extra):
		data = self.run_report(**extra)[1]
		return next(row for row in data if row["purchase_order"] == po_name)

	def test_purchase_order_line_shown_with_values(self):
		po = create_purchase_order(qty=10, rate=500, transaction_date="2026-06-01")

		row = self.po_row(po.name)
		self.assertEqual(row["item_code"], "_Test Item")
		self.assertEqual(row["quantity"], 10)
		self.assertEqual(row["rate"], 500)
		self.assertEqual(row["amount"], 5000)
		self.assertEqual(row["supplier"], "_Test Supplier")

	def test_draft_purchase_order_excluded(self):
		po = create_purchase_order(transaction_date="2026-06-01", do_not_submit=True)

		names = {row["purchase_order"] for row in self.run_report()[1]}
		self.assertNotIn(po.name, names)

	def test_date_range_filters_on_transaction_date(self):
		po = create_purchase_order(transaction_date="2026-06-01")

		in_range = {
			row["purchase_order"] for row in self.run_report(from_date="2026-05-01", to_date="2026-07-01")[1]
		}
		self.assertIn(po.name, in_range)

		out_of_range = {
			row["purchase_order"] for row in self.run_report(from_date="2026-01-01", to_date="2026-03-01")[1]
		}
		self.assertNotIn(po.name, out_of_range)

	def test_item_code_filter(self):
		po = create_purchase_order(
			transaction_date="2026-06-01",
			rm_items=[
				{"item_code": "_Test Item", "qty": 5, "rate": 500, "warehouse": "_Test Warehouse - _TC"},
				{"item_code": "_Test Item 2", "qty": 3, "rate": 200, "warehouse": "_Test Warehouse - _TC"},
			],
		)

		rows = self.run_report(item_code="_Test Item 2")[1]
		self.assertEqual({row["item_code"] for row in rows}, {"_Test Item 2"})
		# the filtered-out line of the same order must not leak in
		self.assertTrue(all(row["purchase_order"] == po.name for row in rows))

	def test_item_group_filter(self):
		# _Test Item is in _Test Item Group; _Test FG Item is in _Test Item Group Desktops
		po_test_group = create_purchase_order(item_code="_Test Item", transaction_date="2026-06-01")
		po_other_group = create_purchase_order(item_code="_Test FG Item", transaction_date="2026-06-01")

		names = {row["purchase_order"] for row in self.run_report(item_group="_Test Item Group")[1]}
		self.assertIn(po_test_group.name, names)
		self.assertNotIn(po_other_group.name, names)

	def test_supplier_filter(self):
		create_purchase_order(supplier="_Test Supplier", transaction_date="2026-06-01")
		create_purchase_order(supplier="_Test Supplier 1", transaction_date="2026-06-01")

		suppliers = {row["supplier"] for row in self.run_report(supplier="_Test Supplier")[1]}
		self.assertEqual(suppliers, {"_Test Supplier"})

	def test_received_quantity_reflects_receipt(self):
		po = create_purchase_order(qty=10, rate=500, transaction_date="2026-06-01")
		create_pr_against_po(po.name, received_qty=4)

		self.assertEqual(self.po_row(po.name)["received_qty"], 4)

	def test_billed_amount_reflects_invoice(self):
		po = create_purchase_order(qty=10, rate=500, transaction_date="2026-06-01")
		pi = make_purchase_invoice(po.name)
		pi.insert()
		pi.submit()

		self.assertEqual(self.po_row(po.name)["billed_amt"], 5000)

	def test_amounts_reported_in_company_currency(self):
		# a USD order must report rate/amount converted to the company's currency (base_* fields)
		po = create_purchase_order(
			do_not_save=True,
			currency="USD",
			qty=10,
			rate=100,
			transaction_date="2026-06-01",
		)
		po.conversion_rate = 80
		po.insert()
		po.submit()

		row = self.po_row(po.name)
		self.assertEqual(row["rate"], 8000)  # 100 USD * 80
		self.assertEqual(row["amount"], 80000)  # 10 * 100 USD * 80

	def test_chart_aggregates_amount_per_item(self):
		create_purchase_order(item_code="_Test Item", qty=2, rate=500, transaction_date="2026-06-01")
		create_purchase_order(item_code="_Test Item", qty=3, rate=500, transaction_date="2026-06-01")

		chart = self.run_report(item_code="_Test Item")[3]
		labels = chart["data"]["labels"]
		values = chart["data"]["datasets"][0]["values"]
		self.assertIn("_Test Item", labels)
		# 2*500 + 3*500 aggregated for the item
		self.assertEqual(values[labels.index("_Test Item")], 2500)
