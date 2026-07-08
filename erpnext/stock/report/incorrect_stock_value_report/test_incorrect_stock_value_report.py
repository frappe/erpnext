# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

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

	def test_balanced_account_has_no_discrepancy(self):
		warehouse = create_warehouse("_Test ISV WH", company=COMPANY)
		account = frappe.get_value("Warehouse", warehouse, "account")
		item = "_Test Item"

		make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=10,
			basic_rate=100,
			company=COMPANY,
			posting_date="2026-02-01",
		)
		make_stock_entry(
			item_code=item,
			from_warehouse=warehouse,
			qty=4,
			company=COMPANY,
			posting_date="2026-03-01",
		)

		rows = self.run_report(account=account)

		offending = [row for row in rows if row.get("warehouse") == warehouse or row.get("item_code") == item]
		self.assertEqual(offending, [], f"Balanced perpetual account flagged as incorrect: {offending}")
