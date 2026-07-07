# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.report.purchase_receipt_trends.purchase_receipt_trends import execute
from erpnext.tests.utils import ERPNextTestSuite

ITEM = "_Test Item"
ITEM_GROUP = "_Test Item Group"
SUPPLIER = "_Test Supplier"


class TestPurchaseReceiptTrends(ERPNextTestSuite):
	def run_report(self, **extra):
		return self.run_report_full(**extra)[1]

	def run_report_full(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2026",
				"period": "Yearly",
				"based_on": "Item",
				"group_by": "",
			}
		)
		filters.update(extra)
		columns, data = execute(filters)[:2]
		return columns, data

	# trend columns are "Label:fieldtype:width" strings; assert by label so the index
	# stays correct across period / based_on / group_by combinations.
	@staticmethod
	def labels(columns):
		return [c.split(":")[0] if isinstance(c, str) else c.get("label") for c in columns]

	def find_row(self, columns, data, match):
		labels = self.labels(columns)
		for row in data:
			if all(row[labels.index(label)] == value for label, value in match.items()):
				return row
		return None

	def value(self, columns, row, label):
		if not row:
			return 0
		return row[self.labels(columns).index(label)] or 0

	def values(self, match, wanted_labels, **extra):
		columns, data = self.run_report_full(**extra)
		row = self.find_row(columns, data, match)
		return {label: self.value(columns, row, label) for label in wanted_labels}

	def test_receipt_qty_in_trend(self):
		# The report sums ALL purchase receipts for the item in the fiscal year, so capture
		# any pre-existing baseline and assert only this receipt's contribution.
		cols = ["_Test Fiscal Year 2026 (Qty)", "_Test Fiscal Year 2026 (Amt)"]
		before = self.values({"Item": ITEM}, cols)
		make_purchase_receipt(
			item_code=ITEM, qty=10, rate=100, company="_Test Company", posting_date="2026-06-01"
		)
		after = self.values({"Item": ITEM}, cols)
		self.assertEqual(after[cols[0]] - before[cols[0]], 10)
		self.assertEqual(after[cols[1]] - before[cols[1]], 1000)

	def test_monthly_period_buckets(self):
		cols = ["Jun (Qty)", "Jun (Amt)", "Total(Qty)", "Total(Amt)"]
		before = self.values({"Item": ITEM}, cols, period="Monthly")
		make_purchase_receipt(
			item_code=ITEM, qty=10, rate=100, company="_Test Company", posting_date="2026-06-01"
		)
		after = self.values({"Item": ITEM}, cols, period="Monthly")
		# the June receipt lands only in the June bucket, and rolls up into the Total columns
		self.assertEqual(after["Jun (Qty)"] - before["Jun (Qty)"], 10)
		self.assertEqual(after["Jun (Amt)"] - before["Jun (Amt)"], 1000)
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 10)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_quarterly_period_buckets(self):
		# 2026-06-01 falls in the Apr-Jun quarter
		cols = ["Apr-Jun (Qty)", "Apr-Jun (Amt)", "Total(Qty)"]
		before = self.values({"Item": ITEM}, cols, period="Quarterly")
		make_purchase_receipt(
			item_code=ITEM, qty=10, rate=100, company="_Test Company", posting_date="2026-06-01"
		)
		after = self.values({"Item": ITEM}, cols, period="Quarterly")
		self.assertEqual(after["Apr-Jun (Qty)"] - before["Apr-Jun (Qty)"], 10)
		self.assertEqual(after["Apr-Jun (Amt)"] - before["Apr-Jun (Amt)"], 1000)
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 10)

	def test_based_on_supplier(self):
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Supplier": SUPPLIER}, cols, based_on="Supplier")
		make_purchase_receipt(
			item_code=ITEM,
			qty=10,
			rate=100,
			supplier=SUPPLIER,
			company="_Test Company",
			posting_date="2026-06-01",
		)
		after = self.values({"Supplier": SUPPLIER}, cols, based_on="Supplier")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 10)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_based_on_item_group(self):
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Item Group": ITEM_GROUP}, cols, based_on="Item Group")
		make_purchase_receipt(
			item_code=ITEM, qty=10, rate=100, company="_Test Company", posting_date="2026-06-01"
		)
		after = self.values({"Item Group": ITEM_GROUP}, cols, based_on="Item Group")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 10)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_group_by_item_under_supplier(self):
		# based_on=Supplier with group_by=Item produces an item-wise breakdown row
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Item": ITEM}, cols, based_on="Supplier", group_by="Item")
		make_purchase_receipt(
			item_code=ITEM,
			qty=10,
			rate=100,
			supplier=SUPPLIER,
			company="_Test Company",
			posting_date="2026-06-01",
		)
		after = self.values({"Item": ITEM}, cols, based_on="Supplier", group_by="Item")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 10)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)
