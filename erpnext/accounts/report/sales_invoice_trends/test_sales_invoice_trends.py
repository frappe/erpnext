# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.sales_invoice_trends.sales_invoice_trends import execute
from erpnext.tests.utils import ERPNextTestSuite

FISCAL_YEAR = "_Test Fiscal Year 2026"
POSTING_DATE = "2026-06-01"


class TestSalesInvoiceTrends(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": FISCAL_YEAR,
				"based_on": "Item",
				"period": "Yearly",
			}
		)
		filters.update(extra)
		columns, data = execute(filters)
		labels = [c.split(":")[0] if isinstance(c, str) else c.get("label") for c in columns]
		return labels, data

	def _cell(self, data, key_label, key_value, col_label, labels):
		"""Return the value at column `col_label` for the row whose first-column
		value equals `key_value`, or 0 if that row does not exist yet."""
		key_idx = labels.index(key_label)
		col_idx = labels.index(col_label)
		for row in data:
			if row[key_idx] == key_value:
				return row[col_idx] or 0
		return 0

	def test_yearly_item_amount_and_total(self):
		# Yearly period => a single "<FY> (Qty)"/"(Amt)" bucket, plus Total(Qty)/Total(Amt).
		labels, before = self.run_report()
		qty_col = f"{FISCAL_YEAR} (Qty)"
		amt_col = f"{FISCAL_YEAR} (Amt)"
		before_qty = self._cell(before, "Item", "_Test Item", qty_col, labels)
		before_amt = self._cell(before, "Item", "_Test Item", amt_col, labels)
		before_tot_qty = self._cell(before, "Item", "_Test Item", "Total(Qty)", labels)
		before_tot_amt = self._cell(before, "Item", "_Test Item", "Total(Amt)", labels)

		create_sales_invoice(item="_Test Item", qty=4, rate=200, posting_date=POSTING_DATE)

		labels, after = self.run_report()
		self.assertEqual(self._cell(after, "Item", "_Test Item", qty_col, labels) - before_qty, 4)
		self.assertEqual(self._cell(after, "Item", "_Test Item", amt_col, labels) - before_amt, 800)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Qty)", labels) - before_tot_qty, 4)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Amt)", labels) - before_tot_amt, 800)

	def test_monthly_lands_in_june_bucket(self):
		# Monthly period => one bucket per month; a 2026-06-01 invoice hits "Jun (Qty)"/"(Amt)".
		labels, before = self.run_report(period="Monthly")
		before_qty = self._cell(before, "Item", "_Test Item", "Jun (Qty)", labels)
		before_amt = self._cell(before, "Item", "_Test Item", "Jun (Amt)", labels)
		before_tot = self._cell(before, "Item", "_Test Item", "Total(Amt)", labels)

		create_sales_invoice(item="_Test Item", qty=3, rate=100, posting_date=POSTING_DATE)

		labels, after = self.run_report(period="Monthly")
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jun (Qty)", labels) - before_qty, 3)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jun (Amt)", labels) - before_amt, 300)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Amt)", labels) - before_tot, 300)
		# Nothing should leak into an unrelated month.
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jan (Amt)", labels), 0)

	def test_quarterly_lands_in_apr_jun_bucket(self):
		# Quarterly period over a Jan-Dec fiscal year => Apr-Jun is the 2nd quarter; June lands there.
		labels, before = self.run_report(period="Quarterly")
		before_qty = self._cell(before, "Item", "_Test Item", "Apr-Jun (Qty)", labels)
		before_amt = self._cell(before, "Item", "_Test Item", "Apr-Jun (Amt)", labels)

		create_sales_invoice(item="_Test Item", qty=5, rate=50, posting_date=POSTING_DATE)

		labels, after = self.run_report(period="Quarterly")
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Apr-Jun (Qty)", labels) - before_qty, 5)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Apr-Jun (Amt)", labels) - before_amt, 250)
		# Jan-Mar quarter must stay untouched.
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jan-Mar (Amt)", labels), 0)

	def test_based_on_customer_total(self):
		# based_on=Customer => first column is "Customer"; the customer's Total(Amt) reflects the sale.
		labels, before = self.run_report(based_on="Customer")
		before_tot_qty = self._cell(before, "Customer", "_Test Customer", "Total(Qty)", labels)
		before_tot_amt = self._cell(before, "Customer", "_Test Customer", "Total(Amt)", labels)

		create_sales_invoice(
			customer="_Test Customer", item="_Test Item", qty=2, rate=300, posting_date=POSTING_DATE
		)

		labels, after = self.run_report(based_on="Customer")
		self.assertEqual(
			self._cell(after, "Customer", "_Test Customer", "Total(Qty)", labels) - before_tot_qty, 2
		)
		self.assertEqual(
			self._cell(after, "Customer", "_Test Customer", "Total(Amt)", labels) - before_tot_amt, 600
		)

	def test_group_by_item_under_customer(self):
		# based_on=Customer + group_by=Item inserts an "Item" breakdown column before the period
		# buckets; the per-item detail row carries the item key and the amount for that customer/item.
		labels, before = self.run_report(based_on="Customer", group_by="Item")
		# In group_by mode the detail rows key off the group_by column ("Item"), so snapshot by item.
		before_amt = self._cell(before, "Item", "_Test Item", "Total(Amt)", labels)

		create_sales_invoice(
			customer="_Test Customer", item="_Test Item", qty=6, rate=100, posting_date=POSTING_DATE
		)

		labels, after = self.run_report(based_on="Customer", group_by="Item")
		self.assertIn("Item", labels)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Amt)", labels) - before_amt, 600)
