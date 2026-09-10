# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.buying.doctype.supplier_quotation.mapper import make_purchase_order
from erpnext.buying.report.supplier_quotation_comparison.supplier_quotation_comparison import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
ITEM = "_Test Item"


class TestSupplierQuotationComparison(ERPNextTestSuite):
	"""The report lists Supplier Quotation item lines so quotes for the same item can
	be compared across suppliers."""

	def make_quotation(self, supplier, qty, rate, uom=None, submit=True):
		item = {"item_code": ITEM, "qty": qty, "rate": rate, "warehouse": "_Test Warehouse - _TC"}
		if uom:
			item["uom"] = uom
		sq = frappe.get_doc(
			{
				"doctype": "Supplier Quotation",
				"supplier": supplier,
				"company": COMPANY,
				"currency": "INR",
				"transaction_date": "2026-06-01",
				"items": [item],
			}
		)
		sq.insert()
		if submit:
			sq.submit()
		return sq

	def run_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, "from_date": "2026-01-01", "to_date": "2026-12-31"})
		filters.update(extra)
		return execute(filters)[1]

	def make_order(self, supplier_quotation, qty):
		purchase_order = make_purchase_order(supplier_quotation.name)
		purchase_order.naming_series = "_T-Purchase Order-"
		purchase_order.items[0].qty = qty
		purchase_order.items[0].schedule_date = add_days(today(), 1)
		purchase_order.insert()
		purchase_order.submit()
		return purchase_order

	def test_no_filters_returns_empty(self):
		self.assertEqual(execute(None)[1], [])

	def test_quotation_line_listed_with_price(self):
		# _Test UOM 1 converts at 10 stock units per qty, so price_per_unit
		# (amount / stock_qty) diverges from base_rate and the division path is tested
		sq = self.make_quotation("_Test Supplier", qty=10, rate=100, uom="_Test UOM 1")

		rows = [r for r in self.run_report(item_code=ITEM) if r.get("quotation") == sq.name]
		self.assertTrue(rows, "Supplier Quotation line missing from report")
		row = rows[0]
		self.assertEqual(row["supplier_name"], "_Test Supplier")
		self.assertEqual(row["qty"], 10)
		self.assertEqual(row["base_rate"], 100)
		self.assertEqual(row["base_amount"], 1000)
		# 1000 amount / (10 qty * 10 conversion) = 10, distinct from the 100 base_rate
		self.assertEqual(row["price_per_unit"], 10)

	def test_compares_multiple_suppliers_for_item(self):
		sq1 = self.make_quotation("_Test Supplier", qty=10, rate=100)
		sq2 = self.make_quotation("_Test Supplier 1", qty=10, rate=120)

		quotes = {r["quotation"]: r for r in self.run_report(item_code=ITEM)}
		self.assertIn(sq1.name, quotes)
		self.assertIn(sq2.name, quotes)
		self.assertEqual(quotes[sq1.name]["base_rate"], 100)
		self.assertEqual(quotes[sq2.name]["base_rate"], 120)

	def test_status_filter(self):
		draft = self.make_quotation("_Test Supplier", qty=10, rate=100, submit=False)
		submitted = self.make_quotation("_Test Supplier 1", qty=10, rate=120)

		def names(**extra):
			return {r["quotation"] for r in self.run_report(item_code=ITEM, **extra)}

		# default (Submitted) hides drafts
		self.assertNotIn(draft.name, names(status="Submitted"))
		self.assertIn(submitted.name, names(status="Submitted"))
		# Draft shows only drafts
		self.assertIn(draft.name, names(status="Draft"))
		self.assertNotIn(submitted.name, names(status="Draft"))
		# blank shows both
		both = names(status="")
		self.assertIn(draft.name, both)
		self.assertIn(submitted.name, both)

	def test_order_status_and_filter(self):
		supplier_quotation = self.make_quotation("_Test Supplier", qty=10, rate=100)

		def get_order_status():
			return next(
				row["order_status"]
				for row in self.run_report(item_code=ITEM)
				if row["quotation"] == supplier_quotation.name
			)

		def quotations_with_status(order_status):
			return {row["quotation"] for row in self.run_report(item_code=ITEM, order_status=order_status)}

		self.assertEqual(get_order_status(), "Not Ordered")
		self.assertIn(supplier_quotation.name, quotations_with_status("Not Ordered"))

		partial_order = self.make_order(supplier_quotation, qty=4)
		self.assertEqual(get_order_status(), "Partially Ordered")
		self.assertIn(supplier_quotation.name, quotations_with_status("Partially Ordered"))
		self.assertNotIn(supplier_quotation.name, quotations_with_status("Ordered"))

		complete_order = self.make_order(supplier_quotation, qty=6)
		self.assertEqual(get_order_status(), "Ordered")
		self.assertIn(supplier_quotation.name, quotations_with_status("Ordered"))

		complete_order.cancel()
		self.assertEqual(get_order_status(), "Partially Ordered")

		partial_order.cancel()
		self.assertEqual(get_order_status(), "Not Ordered")
