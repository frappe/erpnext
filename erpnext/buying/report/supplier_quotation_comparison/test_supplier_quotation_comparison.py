# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.buying.report.supplier_quotation_comparison.supplier_quotation_comparison import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
ITEM = "_Test Item"


class TestSupplierQuotationComparison(ERPNextTestSuite):
	"""The report lists Supplier Quotation item lines so quotes for the same item can
	be compared across suppliers."""

	def make_quotation(self, supplier, qty, rate, uom=None):
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
		sq.submit()
		return sq

	def run_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, "from_date": "2026-01-01", "to_date": "2026-12-31"})
		filters.update(extra)
		return execute(filters)[1]

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
