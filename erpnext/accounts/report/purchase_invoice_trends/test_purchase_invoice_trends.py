# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.purchase_invoice_trends.purchase_invoice_trends import execute
from erpnext.tests.utils import ERPNextTestSuite

FISCAL_YEAR = "_Test Fiscal Year 2026"
COMPANY = "_Test Company"
SUPPLIER = "_Test Supplier"
ITEM = "_Test Item"
POSTING_DATE = "2026-06-01"


def make_dated_purchase_invoice(qty, rate):
	# make_purchase_invoice ignores posting_date unless posting time is explicitly set, so build the
	# invoice unsubmitted, pin the posting date, then submit to land it in the intended period bucket.
	pi = make_purchase_invoice(
		supplier=SUPPLIER, item_code=ITEM, qty=qty, rate=rate, posting_date=POSTING_DATE, do_not_submit=1
	)
	pi.set_posting_time = 1
	pi.posting_date = POSTING_DATE
	pi.submit()
	return pi


class TestPurchaseInvoiceTrends(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": COMPANY,
				"fiscal_year": FISCAL_YEAR,
				"period": "Yearly",
				"based_on": "Item",
			}
		)
		filters.update(extra)
		columns, data = execute(filters)
		labels = [c.split(":")[0] if isinstance(c, str) else c.get("label") for c in columns]
		return labels, data

	@staticmethod
	def _cell(labels, row, label):
		return row[labels.index(label)]

	def _find_row(self, data, key):
		for row in data:
			if row and row[0] == key:
				return row
		return None

	def test_yearly_item_qty_and_amount(self):
		labels_before, data_before = self.run_report()
		before = self._find_row(data_before, ITEM)

		qty, rate = 4, 250
		make_dated_purchase_invoice(qty, rate)

		labels, data = self.run_report()
		self.assertIn("Item", labels)
		self.assertIn("Item Name", labels)
		self.assertIn("Currency", labels)
		self.assertIn("Total(Qty)", labels)
		self.assertIn("Total(Amt)", labels)
		# Yearly period bucket uses the fiscal year name as the label prefix
		self.assertIn(f"{FISCAL_YEAR} (Qty)", labels)
		self.assertIn(f"{FISCAL_YEAR} (Amt)", labels)

		row = self._find_row(data, ITEM)
		self.assertIsNotNone(row)

		before_qty = self._cell(labels_before, before, f"{FISCAL_YEAR} (Qty)") if before else 0
		before_amt = self._cell(labels_before, before, f"{FISCAL_YEAR} (Amt)") if before else 0
		before_tqty = self._cell(labels_before, before, "Total(Qty)") if before else 0
		before_tamt = self._cell(labels_before, before, "Total(Amt)") if before else 0

		self.assertEqual(self._cell(labels, row, f"{FISCAL_YEAR} (Qty)") - before_qty, qty)
		self.assertEqual(self._cell(labels, row, f"{FISCAL_YEAR} (Amt)") - before_amt, qty * rate)
		self.assertEqual(self._cell(labels, row, "Total(Qty)") - before_tqty, qty)
		self.assertEqual(self._cell(labels, row, "Total(Amt)") - before_tamt, qty * rate)

	def test_monthly_bucket(self):
		labels_before, data_before = self.run_report(period="Monthly")
		before = self._find_row(data_before, ITEM)

		qty, rate = 3, 100
		make_dated_purchase_invoice(qty, rate)

		labels, data = self.run_report(period="Monthly")
		# posting_date 2026-06-01 -> June bucket
		self.assertIn("Jun (Qty)", labels)
		self.assertIn("Jun (Amt)", labels)

		row = self._find_row(data, ITEM)
		before_qty = self._cell(labels_before, before, "Jun (Qty)") if before else 0
		before_tamt = self._cell(labels_before, before, "Total(Amt)") if before else 0

		self.assertEqual(self._cell(labels, row, "Jun (Qty)") - before_qty, qty)
		self.assertEqual(self._cell(labels, row, "Total(Amt)") - before_tamt, qty * rate)

	def test_quarterly_bucket(self):
		labels_before, data_before = self.run_report(period="Quarterly")
		before = self._find_row(data_before, ITEM)

		qty, rate = 2, 150
		make_dated_purchase_invoice(qty, rate)

		labels, data = self.run_report(period="Quarterly")
		# 2026-06-01 falls in the Apr-Jun quarter
		self.assertIn("Apr-Jun (Qty)", labels)
		self.assertIn("Apr-Jun (Amt)", labels)

		row = self._find_row(data, ITEM)
		before_qty = self._cell(labels_before, before, "Apr-Jun (Qty)") if before else 0
		before_amt = self._cell(labels_before, before, "Apr-Jun (Amt)") if before else 0

		self.assertEqual(self._cell(labels, row, "Apr-Jun (Qty)") - before_qty, qty)
		self.assertEqual(self._cell(labels, row, "Apr-Jun (Amt)") - before_amt, qty * rate)

	def test_based_on_supplier(self):
		labels_before, data_before = self.run_report(based_on="Supplier")
		before = self._find_row(data_before, SUPPLIER)

		qty, rate = 5, 200
		make_dated_purchase_invoice(qty, rate)

		labels, data = self.run_report(based_on="Supplier")
		self.assertIn("Supplier", labels)
		self.assertIn("Supplier Name", labels)
		self.assertIn("Supplier Group", labels)

		row = self._find_row(data, SUPPLIER)
		self.assertIsNotNone(row)

		before_tqty = self._cell(labels_before, before, "Total(Qty)") if before else 0
		before_tamt = self._cell(labels_before, before, "Total(Amt)") if before else 0

		self.assertEqual(self._cell(labels, row, "Total(Qty)") - before_tqty, qty)
		self.assertEqual(self._cell(labels, row, "Total(Amt)") - before_tamt, qty * rate)

	def test_group_by_item_under_supplier(self):
		labels_before, data_before = self.run_report(based_on="Supplier", group_by="Item")
		# group_by inserts an "Item" column; the item breakdown row carries the item key there
		item_idx = labels_before.index("Item")
		before = None
		for r in data_before:
			if r and r[0] != SUPPLIER and r[item_idx] == ITEM:
				before = r
				break

		qty, rate = 6, 300
		make_dated_purchase_invoice(qty, rate)

		labels, data = self.run_report(based_on="Supplier", group_by="Item")
		self.assertIn("Item", labels)

		item_idx = labels.index("Item")
		row = None
		for r in data:
			if r and r[0] != SUPPLIER and r[0] != "'Total'" and r[item_idx] == ITEM:
				row = r
				break
		self.assertIsNotNone(row)

		before_tqty = self._cell(labels_before, before, "Total(Qty)") if before else 0
		before_tamt = self._cell(labels_before, before, "Total(Amt)") if before else 0

		self.assertEqual(self._cell(labels, row, "Total(Qty)") - before_tqty, qty)
		self.assertEqual(self._cell(labels, row, "Total(Amt)") - before_tamt, qty * rate)
