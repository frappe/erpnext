# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Helpers to run the financial reports in the cash basis tests."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis import CASH
from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import US_COMPANY, set_company_method

NON_PERIOD_FIELDS = {
	"account",
	"currency",
	"total",
	"account_name",
	"parent_account",
	"indent",
	"opening_balance",
}


class ReportTestCase(CashBasisTestCase):
	"""The reports read the unapplied settings of the Company, so each test sets the method Cash."""

	def setUp(self):
		super().setUp()
		self.company_doc = set_company_method(US_COMPANY, CASH, treatment=self.treatment)
		self.unapplied_arguments = {
			"unapplied_treatment": self.treatment,
			"unapplied_accounts": {
				"Customer": self.company_doc.unapplied_cash_receipts_account,
				"Supplier": self.company_doc.unapplied_cash_payments_account,
			},
		}
		self.unapplied_accounts = set(self.unapplied_arguments["unapplied_accounts"].values()) - {None}

	def report_filters(self, from_date, to_date, periodicity="Yearly", **extra):
		return frappe._dict(
			{
				"company": US_COMPANY,
				"filter_based_on": "Date Range",
				"period_start_date": from_date,
				"period_end_date": to_date,
				"periodicity": periodicity,
				"accumulated_values": 0,
				**extra,
			}
		)

	def run_report(self, execute, from_date, to_date, **extra):
		return execute(self.report_filters(from_date, to_date, **extra))


def period_keys(columns) -> list[str]:
	return [c["fieldname"] for c in columns if c.get("fieldname") not in NON_PERIOD_FIELDS]


def report_values(result, account, key=None) -> float:
	"""The value of an account row in the last period column, or in the given column."""
	columns, data = result[0], result[1]
	key = key or period_keys(columns)[-1]
	for row in data:
		if row and row.get("account") == account:
			return flt(row.get(key), 2)
	return 0.0


def row_value(result, label_field, label, key=None) -> float:
	"""The value of a row found by a label, for example the net profit row."""
	columns, data = result[0], result[1]
	key = key or period_keys(columns)[-1]
	for row in data:
		if row and label in str(row.get(label_field) or ""):
			return flt(row.get(key), 2)
	return 0.0


def comparable(result):
	"""Columns and data of a report result, for an exact comparison."""
	return frappe.as_json([result[0], result[1]])
