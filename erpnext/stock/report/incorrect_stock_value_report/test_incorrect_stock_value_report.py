# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.incorrect_stock_value_report.incorrect_stock_value_report import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company with perpetual inventory"


class TestIncorrectStockValueReport(ERPNextTestSuite):
	"""Correctness tests for the Incorrect Stock Value report.

	The report is a corruption detector: it walks stock account postings and flags
	dates/vouchers where the stock ledger value diverges from the GL balance. Clean,
	balanced perpetual transactions keep ledger value == GL balance, so they must
	never surface as discrepancy rows.
	"""

	def run_report(self, **extra):
		filters = frappe._dict(
			company=COMPANY,
			from_date="2026-01-01",
			to_date="2026-12-31",
		)
		filters.update(extra)
		return list(execute(filters)[1])

	def test_account_is_required(self):
		self.assertRaises(frappe.MandatoryError, self.run_report)

	def make_stock(self, posting_date):
		warehouse = create_warehouse("_Test ISV WH", company=COMPANY)
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=10,
			basic_rate=100,
			company=COMPANY,
			posting_date=posting_date,
		)
		return warehouse, frappe.get_value("Warehouse", warehouse, "account"), item

	def issue(self, item, warehouse, qty, posting_date):
		entry = make_stock_entry(
			item_code=item, from_warehouse=warehouse, qty=qty, company=COMPANY, posting_date=posting_date
		)
		return frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name}, "name")

	def test_differences_dated_today_are_checked(self):
		warehouse, account, item = self.make_stock(add_days(today(), -5))
		sle = self.issue(item, warehouse, 2, today())
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_value_difference", -150)

		rows = self.run_report(account=account, from_date=add_days(today(), -1))

		self.assertEqual([row.name for row in rows], [sle])

	def test_later_entries_of_the_same_day_follow_the_running_value(self):
		warehouse, account, item = self.make_stock(add_days(today(), -5))
		other_item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		make_stock_entry(
			item_code=other_item,
			to_warehouse=warehouse,
			qty=10,
			basic_rate=100,
			company=COMPANY,
			posting_date=add_days(today(), -5),
		)
		self.issue(item, warehouse, 2, add_days(today(), -3))
		self.issue(item, warehouse, 3, add_days(today(), -3))
		changed = self.issue(other_item, warehouse, 1, add_days(today(), -3))
		frappe.db.set_value("Stock Ledger Entry", changed, "stock_value_difference", -50)

		rows = self.run_report(account=account, from_date=add_days(today(), -4))

		self.assertEqual([row.name for row in rows], [changed])

	def test_wrong_stock_value_is_found_when_the_ledger_matches_the_accounts(self):
		warehouse, account, item = self.make_stock(add_days(today(), -5))
		sle = self.issue(item, warehouse, 2, add_days(today(), -3))
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_value", 1300)

		rows = self.run_report(account=account, from_date=add_days(today(), -4))

		self.assertEqual([(row.name, row.difference_value) for row in rows], [(sle, 500)])

	def test_rows_of_warehouses_under_another_account_are_left_out(self):
		from unittest.mock import patch

		warehouse, account, item = self.make_stock(add_days(today(), -5))
		sle = self.issue(item, warehouse, 2, add_days(today(), -3))
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_value", 1300)

		module = "erpnext.stock.report.incorrect_stock_value_report.incorrect_stock_value_report"
		with patch(f"{module}.get_account_warehouses", return_value=["_Test Warehouse - TCP1"]):
			rows = self.run_report(account=account, from_date=add_days(today(), -4))

		self.assertNotIn(sle, [row.name for row in rows])
