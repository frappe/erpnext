# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher import (
	process_individual_date,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessPeriodClosingVoucher(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 0)
		self.company = "_Test Company"

	def make_period_closing_voucher(self, posting_date, submit=True):
		fy = get_fiscal_year(posting_date, company="_Test Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": posting_date or today(),
				"period_start_date": fy[1],
				"period_end_date": fy[2],
				"company": self.company,
				"fiscal_year": fy[0],
				"closing_account_head": "Retained Earnings - _TC",
				"remarks": "closing",
			}
		)
		pcv.insert()
		if submit:
			pcv.submit()

		return pcv

	def make_process_pcv(self):
		self.pcv = self.make_period_closing_voucher(posting_date=today(), submit=False)
		ppcv = frappe.get_doc(
			{
				"doctype": "Process Period Closing Voucher",
				"parent_pcv": self.pcv.name,
			}
		)
		ppcv.save()
		return ppcv

	def set_processing_date_status(self, row_name, status):
		frappe.db.set_value(
			"Process Period Closing Voucher Detail",
			row_name,
			"status",
			status,
		)

	def get_row_name(self, ppcv_name, rpt_type, parentfield):
		return frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": ppcv_name, "report_type": rpt_type, "parentfield": parentfield},
			order_by="report_type, idx",
			pluck="name",
			limit=1,
		)[0]

	def get_processing_date_closing_balance(self, row_name):
		return frappe.db.get_value(
			"Process Period Closing Voucher Detail",
			row_name,
			"closing_balance",
		)

	def test_opening_balance_double_counting(self):
		ppcv = self.make_process_pcv()
		self.assertEqual(self.pcv.is_first_period_closing_voucher(), True)
		opening_jv = make_journal_entry(
			posting_date=today(),
			amount=10,
			account1="Cash - _TC",
			account2="Debtors - _TC",
			company=self.company,
			save=False,
		)
		opening_jv.accounts[1].party_type = "Customer"
		opening_jv.accounts[1].party = "_Test Customer"
		opening_jv.is_opening = "Yes"
		opening_jv.save()
		opening_jv.submit()

		jv = make_journal_entry(
			posting_date=today(),
			amount=120,
			account1="Debtors - _TC",
			account2="Sales - _TC",
			company=self.company,
			save=False,
		)
		jv.accounts[0].party_type = "Customer"
		jv.accounts[0].party = "_Test Customer"
		jv.save()
		jv.submit()

		# P&L balance
		parentfield = "normal_balances"
		rpt_type = "Profit and Loss"
		# status has to be set to 'Running' for logic to run
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 1)
		expected_pl = {
			"account": "Sales - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 0.0,
			"credit": 120.0,
			"debit_in_account_currency": 0.0,
			"credit_in_account_currency": 120.0,
		}
		for k in expected_pl.keys():
			with self.subTest(k):
				self.assertEqual(expected_pl[k], bal[0][k])

		# Balance sheet balance
		rpt_type = "Balance Sheet"
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 1)
		expected_bs = {
			"account": "Debtors - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 120.0,
			"credit": 0.0,
			"debit_in_account_currency": 120.0,
			"credit_in_account_currency": 0.0,
		}
		for k in expected_bs.keys():
			with self.subTest(k):
				self.assertEqual(expected_bs[k], bal[0][k])

		# Opening balance
		parentfield = "z_opening_balances"
		rpt_type = "Balance Sheet"
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 2)
		opening_cash = next(x for x in bal if x["account"] == "Cash - _TC")
		expected_opening_cash = {
			"account": "Cash - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 10.0,
			"credit": 0.0,
			"debit_in_account_currency": 10.0,
			"credit_in_account_currency": 0.0,
			"account_currency": "INR",
		}
		for k in expected_opening_cash.keys():
			with self.subTest(k):
				self.assertEqual(expected_opening_cash[k], opening_cash[k])

		opening_debtors = next(x for x in bal if x["account"] == "Debtors - _TC")
		expected_opening_debtors = {
			"account": "Debtors - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 0.0,
			"credit": 10.0,
			"debit_in_account_currency": 0.0,
			"credit_in_account_currency": 10.0,
			"account_currency": "INR",
		}
		for k in expected_opening_debtors.keys():
			with self.subTest(k):
				self.assertEqual(expected_opening_debtors[k], opening_debtors[k])
