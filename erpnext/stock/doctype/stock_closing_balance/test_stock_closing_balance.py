# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import prepare_closing_stock_balance
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


class TestStockClosingBalance(ERPNextTestSuite):
	def make_closing(self, to_date):
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			entry = frappe.get_doc(
				doctype="Stock Closing Entry", company=COMPANY, from_date=to_date, to_date=to_date
			).submit()

		prepare_closing_stock_balance(entry.name)
		return entry.name

	def get_closing_row(self, closing, item):
		return frappe.db.get_value(
			"Stock Closing Balance",
			{"stock_closing_entry": closing, "item_code": item, "batch_no": ("is", "not set")},
			["actual_qty", "stock_value", "valuation_rate", "fifo_queue"],
			as_dict=True,
		)

	def test_closing_stores_stock_value_and_valuation_rate(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		for qty, rate in ((10, 100), (8, 135)):
			make_stock_entry(
				item_code=item, target=WAREHOUSE, qty=qty, rate=rate, posting_date=add_days(today(), -20)
			)

		closing = self.make_closing(add_days(today(), -10))
		row = self.get_closing_row(closing, item)

		self.assertEqual(row.stock_value, 2080)
		self.assertAlmostEqual(row.valuation_rate, 2080 / 18, 2)

		filters = frappe._dict(
			company=COMPANY, from_date=add_days(today(), -5), to_date=today(), item_code=[item]
		)
		report_row = stock_balance(filters)[1][0]
		self.assertAlmostEqual(report_row["val_rate"], 2080 / 18, 2)
