# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, today
from erpnext.accounts.utils import get_fiscal_year, now
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

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

	def test_cost_center_wise_posting(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()

		cost_center1 = create_cost_center("Test Cost Center 1")
		cost_center2 = create_cost_center("Test Cost Center 2")

		create_sales_invoice(
			company=company,
			cost_center=cost_center1,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=400,
			debit_to="Debtors - TPC"
		)
		create_sales_invoice(
			company=company,
			cost_center=cost_center2,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=200,
			debit_to="Debtors - TPC"
		)

		pcv = frappe.get_doc({
			"transaction_date": today(),
			"posting_date": today(),
			"fiscal_year": get_fiscal_year(today())[0],
			"company": "Test PCV Company",
			"cost_center_wise_pnl": 1,
			"closing_account_head": surplus_account,
			"remarks": "Test",
			"doctype": "Period Closing Voucher"
		})
		pcv.insert()
		pcv.submit()

		expected_gle = (
			('Sales - TPC', 200.0, 0.0, cost_center2),
			(surplus_account, 0.0, 200.0, cost_center2),
			('Sales - TPC', 400.0, 0.0, cost_center1),
			(surplus_account, 0.0, 400.0, cost_center1)
		)

		pcv_gle = frappe.db.sql("""
			select account, debit, credit, cost_center from `tabGL Entry` where voucher_no=%s
		""", (pcv.name))

		self.assertTrue(pcv_gle, expected_gle)

	def make_period_closing_voucher(self):
		pcv = frappe.get_doc({
			"doctype": "Period Closing Voucher",
			"closing_account_head": "_Test Account Reserves and Surplus - _TC",
			"company": "_Test Company",
			"fiscal_year": get_fiscal_year(today(), company="_Test Company")[0],
			"posting_date": today(),
			"cost_center": "_Test Cost Center - _TC",
			"remarks": "test"
		})
		pcv.insert()
		pcv.submit()

		return pcv

def create_company():
	company = frappe.get_doc({
		'doctype': 'Company',
		'company_name': "Test PCV Company",
		'country': 'United States',
		'default_currency': 'USD'
	})		
	company.insert(ignore_if_duplicate = True)
	return company.name

def create_account():
	account = frappe.get_doc({
		"account_name": "Reserve and Surplus",
		"is_group": 0,
		"company": "Test PCV Company",
		"root_type": "Liability",
		"report_type": "Balance Sheet",
		"account_currency": "USD",
		"parent_account": "Current Liabilities - TPC",
		"doctype": "Account"
	}).insert(ignore_if_duplicate = True)
	return account.name

def create_cost_center(cc_name):
	costcenter = frappe.get_doc({
		"company": "Test PCV Company",
		"cost_center_name": cc_name,
		"doctype": "Cost Center",
		"parent_cost_center": "Test PCV Company - TPC"
	})
	costcenter.insert(ignore_if_duplicate = True)
	return costcenter.name

test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")
