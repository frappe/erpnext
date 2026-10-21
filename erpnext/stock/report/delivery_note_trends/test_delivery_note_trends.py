# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.delivery_note_trends.delivery_note_trends import execute

ITEM = "_Test Item"
OTHER_ITEM = "_Test Item 2"
WAREHOUSE = "Stores - _TC"
CUSTOMER = "_Test Customer"
POSTING_DATE = "2026-06-01"
FISCAL_YEAR = get_fiscal_year(POSTING_DATE)[0]


class TestDeliveryNoteTrends(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report_full(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": FISCAL_YEAR,
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

	def total_amount(self, **extra):
		# the report's own consolidated total row, which must follow the filtered rows
		columns, data = self.run_report_full(**extra)
		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		return total_row[self.labels(columns).index("Total(Amt)")] or 0

	def deliver(self, qty=5, rate=200, customer=CUSTOMER, posting_date=POSTING_DATE, item_code=ITEM):
		# stock the item first so the delivery note can ship, then deliver
		make_stock_entry(
			item_code=item_code, to_warehouse=WAREHOUSE, qty=qty + 10, rate=100, posting_date=posting_date
		)
		delivery_note = create_delivery_note(
			item_code=item_code,
			warehouse=WAREHOUSE,
			qty=qty,
			rate=rate,
			customer=customer,
			company="_Test Company",
			posting_date=posting_date,
			do_not_save=1,
		)
		# v15 does not populate this field in the Delivery Note test helper.
		delivery_note.territory = frappe.db.get_value("Customer", customer, "territory")
		delivery_note.insert().submit()

	def test_delivery_qty_in_trend(self):
		# A Delivery Note of qty 5 @ rate 200 sums to qty 5 / amount 1000 (base_net_amount)
		# in the yearly bucket and the Total columns.
		cols = [f"{FISCAL_YEAR} (Qty)", f"{FISCAL_YEAR} (Amt)", "Total(Qty)", "Total(Amt)"]
		before = self.values({"Item": ITEM}, cols)
		self.deliver()
		after = self.values({"Item": ITEM}, cols)
		self.assertEqual(after[cols[0]] - before[cols[0]], 5)
		self.assertEqual(after[cols[1]] - before[cols[1]], 1000)
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_monthly_period_buckets(self):
		cols = ["Jun (Qty)", "Jun (Amt)", "Total(Qty)", "Total(Amt)"]
		before = self.values({"Item": ITEM}, cols, period="Monthly")
		self.deliver(posting_date="2026-06-01")
		after = self.values({"Item": ITEM}, cols, period="Monthly")
		# the June delivery lands only in the June bucket, and rolls up into the Total columns
		self.assertEqual(after["Jun (Qty)"] - before["Jun (Qty)"], 5)
		self.assertEqual(after["Jun (Amt)"] - before["Jun (Amt)"], 1000)
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_quarterly_period_buckets(self):
		# 2026-06-01 falls in the Apr-Jun quarter
		cols = ["Apr-Jun (Qty)", "Apr-Jun (Amt)", "Total(Qty)"]
		before = self.values({"Item": ITEM}, cols, period="Quarterly")
		self.deliver(posting_date="2026-06-01")
		after = self.values({"Item": ITEM}, cols, period="Quarterly")
		self.assertEqual(after["Apr-Jun (Qty)"] - before["Apr-Jun (Qty)"], 5)
		self.assertEqual(after["Apr-Jun (Amt)"] - before["Apr-Jun (Amt)"], 1000)
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)

	def test_based_on_customer(self):
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Customer": CUSTOMER}, cols, based_on="Customer")
		self.deliver(customer=CUSTOMER)
		after = self.values({"Customer": CUSTOMER}, cols, based_on="Customer")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_based_on_territory(self):
		territory = frappe.db.get_value("Customer", CUSTOMER, "territory")
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Territory": territory}, cols, based_on="Territory")
		self.deliver(customer=CUSTOMER)
		after = self.values({"Territory": territory}, cols, based_on="Territory")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_group_by_item_under_customer(self):
		# based_on=Customer with group_by=Item produces an item-wise breakdown row
		cols = ["Total(Qty)", "Total(Amt)"]
		before = self.values({"Item": ITEM}, cols, based_on="Customer", group_by="Item")
		self.deliver(customer=CUSTOMER)
		after = self.values({"Item": ITEM}, cols, based_on="Customer", group_by="Item")
		self.assertEqual(after["Total(Qty)"] - before["Total(Qty)"], 5)
		self.assertEqual(after["Total(Amt)"] - before["Total(Amt)"], 1000)

	def test_item_filter_restricts_rows(self):
		self.deliver()
		self.deliver(qty=3, rate=100, item_code=OTHER_ITEM)
		columns, data = self.run_report_full(item_code=[ITEM])
		items = {row[self.labels(columns).index("Item")] for row in data}
		self.assertIn(ITEM, items)
		self.assertNotIn(OTHER_ITEM, items)

	def test_item_filter_narrows_total(self):
		# the excluded item's 300 must not reach the total the footer adds up
		before = self.total_amount(item_code=[ITEM])
		self.deliver()
		self.deliver(qty=3, rate=100, item_code=OTHER_ITEM)
		after = self.total_amount(item_code=[ITEM])
		self.assertEqual(after - before, 1000)

	def test_item_filter_accepts_multiple_items(self):
		before = self.total_amount(item_code=[ITEM, OTHER_ITEM])
		self.deliver()
		self.deliver(qty=3, rate=100, item_code=OTHER_ITEM)
		after = self.total_amount(item_code=[ITEM, OTHER_ITEM])
		self.assertEqual(after - before, 1300)

	def test_item_filter_applies_under_group_by(self):
		# group_by runs its own per-row queries, so the filter has to reach those too
		self.deliver()
		self.deliver(qty=3, rate=100, item_code=OTHER_ITEM)
		columns, data = self.run_report_full(based_on="Customer", group_by="Item", item_code=[ITEM])
		items = {row[self.labels(columns).index("Item")] for row in data}
		self.assertIn(ITEM, items)
		self.assertNotIn(OTHER_ITEM, items)

	def test_item_filter_accepts_bare_string(self):
		# the desk always sends a list, but a direct API call may pass one item code
		self.deliver()
		self.deliver(qty=3, rate=100, item_code=OTHER_ITEM)
		columns, data = self.run_report_full(item_code=ITEM)
		items = {row[self.labels(columns).index("Item")] for row in data}
		self.assertIn(ITEM, items)
		self.assertNotIn(OTHER_ITEM, items)
