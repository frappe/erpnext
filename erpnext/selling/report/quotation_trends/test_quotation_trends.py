# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.report.quotation_trends.quotation_trends import execute
from erpnext.tests.utils import ERPNextTestSuite

FISCAL_YEAR = "_Test Fiscal Year 2026"
TXN_DATE = "2026-06-01"


class TestQuotationTrends(ERPNextTestSuite):
	"""The trends report buckets submitted Quotation quantities/amounts by period
	(Yearly/Monthly) for the chosen `based_on` dimension (Item, Customer, ...)."""

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
		result = execute(filters)
		columns, data = result[0], result[1]
		labels = [c.split(":")[0] if isinstance(c, str) else c.get("label") for c in columns]
		return labels, data

	def _cell(self, data, key_label, key_value, col_label, labels):
		"""Value at column `col_label` for the row whose `key_label` column equals
		`key_value`, or 0 when that row doesn't exist yet."""
		key_idx = labels.index(key_label)
		col_idx = labels.index(col_label)
		for row in data:
			if row[key_idx] == key_value:
				return row[col_idx] or 0
		return 0

	def test_yearly_item_amount_and_total(self):
		# Yearly period => a single "<FY> (Qty)"/"(Amt)" bucket plus Total(Qty)/Total(Amt).
		labels, before = self.run_report()
		qty_col = f"{FISCAL_YEAR} (Qty)"
		amt_col = f"{FISCAL_YEAR} (Amt)"
		before_qty = self._cell(before, "Item", "_Test Item", qty_col, labels)
		before_amt = self._cell(before, "Item", "_Test Item", amt_col, labels)
		before_tot_qty = self._cell(before, "Item", "_Test Item", "Total(Qty)", labels)
		before_tot_amt = self._cell(before, "Item", "_Test Item", "Total(Amt)", labels)

		make_quotation(item="_Test Item", qty=4, rate=200, transaction_date=TXN_DATE)

		labels, after = self.run_report()
		self.assertEqual(self._cell(after, "Item", "_Test Item", qty_col, labels) - before_qty, 4)
		self.assertEqual(self._cell(after, "Item", "_Test Item", amt_col, labels) - before_amt, 800)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Qty)", labels) - before_tot_qty, 4)
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Total(Amt)", labels) - before_tot_amt, 800)

	def test_monthly_lands_in_june_bucket(self):
		# Monthly period => one bucket per month; a 2026-06-01 quotation hits "Jun (Qty)"/"(Amt)".
		labels, before = self.run_report(period="Monthly")
		before_jun_qty = self._cell(before, "Item", "_Test Item", "Jun (Qty)", labels)
		before_jun_amt = self._cell(before, "Item", "_Test Item", "Jun (Amt)", labels)
		before_may_qty = self._cell(before, "Item", "_Test Item", "May (Qty)", labels)

		make_quotation(item="_Test Item", qty=3, rate=100, transaction_date=TXN_DATE)

		labels, after = self.run_report(period="Monthly")
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jun (Qty)", labels) - before_jun_qty, 3)
		# the amount path is a separate SUM(base_net_amount) case, so assert it too
		self.assertEqual(self._cell(after, "Item", "_Test Item", "Jun (Amt)", labels) - before_jun_amt, 300)
		# nothing was quoted in May, so that bucket is unchanged
		self.assertEqual(self._cell(after, "Item", "_Test Item", "May (Qty)", labels) - before_may_qty, 0)

	def test_based_on_customer_groups_amount_by_party(self):
		# based_on Customer keys rows on the "Party" column (the customer id)
		labels, before = self.run_report(based_on="Customer")
		amt_col = f"{FISCAL_YEAR} (Amt)"
		before_amt = self._cell(before, "Party", "_Test Customer", amt_col, labels)

		make_quotation(
			party_name="_Test Customer", item="_Test Item", qty=2, rate=150, transaction_date=TXN_DATE
		)

		labels, after = self.run_report(based_on="Customer")
		self.assertEqual(self._cell(after, "Party", "_Test Customer", amt_col, labels) - before_amt, 300)
