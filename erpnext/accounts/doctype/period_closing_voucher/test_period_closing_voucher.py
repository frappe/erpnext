# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, today
from erpnext.accounts.utils import get_fiscal_year, now
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestPeriodClosingVoucher(unittest.TestCase):
	def test_closing_entry(self):
		year_start_date = get_fiscal_year(today(), company="_Test Company")[1]

		make_journal_entry("_Test Bank - _TC", "Sales - _TC", 400,
			"_Test Cost Center - _TC", posting_date=now(), submit=True)

		make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 600, "_Test Cost Center - _TC", posting_date=now(), submit=True)

		random_expense_account = frappe.db.sql("""
			select t1.account,
				sum(t1.debit) - sum(t1.credit) as balance,
				sum(t1.debit_in_account_currency) - sum(t1.credit_in_account_currency) \
					as balance_in_account_currency
			from `tabGL Entry` t1, `tabAccount` t2
			where t1.account = t2.name and t2.root_type = 'Expense'
				and t2.docstatus < 2 and t2.company = '_Test Company'
				and t1.posting_date between %s and %s
			group by t1.account
			having sum(t1.debit) > sum(t1.credit)
			limit 1""", (year_start_date, today()), as_dict=True)

		profit_or_loss = frappe.db.sql("""select sum(t1.debit) - sum(t1.credit) as balance
			from `tabGL Entry` t1, `tabAccount` t2
			where t1.account = t2.name and t2.report_type = 'Profit and Loss'
			and t2.docstatus < 2 and t2.company = '_Test Company'
			and t1.posting_date between %s and %s""", (year_start_date, today()))

		profit_or_loss = flt(profit_or_loss[0][0]) if profit_or_loss else 0

		pcv = self.make_period_closing_voucher()

		# Check value for closing account
		gle_amount_for_closing_account = frappe.db.sql("""select debit - credit
			from `tabGL Entry` where voucher_type='Period Closing Voucher' and voucher_no=%s
			and account = '_Test Account Reserves and Surplus - _TC'""", pcv.name)

		gle_amount_for_closing_account = flt(gle_amount_for_closing_account[0][0]) \
			if gle_amount_for_closing_account else 0

		self.assertEqual(gle_amount_for_closing_account, profit_or_loss)

		if random_expense_account:
			# Check posted value for teh above random_expense_account
			gle_for_random_expense_account = frappe.db.sql("""
				select sum(debit - credit) as amount,
					sum(debit_in_account_currency - credit_in_account_currency) as amount_in_account_currency
				from `tabGL Entry`
				where voucher_type='Period Closing Voucher' and voucher_no=%s and account =%s""",
				(pcv.name, random_expense_account[0].account), as_dict=True)

			self.assertEqual(gle_for_random_expense_account[0].amount, -1*random_expense_account[0].balance)
			self.assertEqual(gle_for_random_expense_account[0].amount_in_account_currency,
				-1*random_expense_account[0].balance_in_account_currency)

	def make_period_closing_voucher(self):
		print(frappe.db.sql("select account, cost_center, voucher_type, voucher_no, company from `tabGL Entry` where account = 'Expenses Included In Valuation - _TC' and cost_center = 'Main - WP'"))
		pcv = frappe.get_doc({
			"doctype": "Period Closing Voucher",
			"closing_account_head": "_Test Account Reserves and Surplus - _TC",
			"company": "_Test Company",
			"fiscal_year": get_fiscal_year(today(), company="_Test Company")[0],
			"posting_date": today(),
			"remarks": "test"
		})
		pcv.insert()
		pcv.submit()

		return pcv


test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")
