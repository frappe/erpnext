# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.finance_book.test_finance_book import create_finance_book
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import get_fiscal_year, now


class TestPeriodClosingVoucher(unittest.TestCase):
	def test_closing_entry(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		jv1 = make_journal_entry(
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			posting_date=now(),
			save=False,
		)
		jv1.company = company
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			amount=600,
			account1="Cost of Goods Sold - TPC",
			account2="Cash - TPC",
			cost_center=cost_center,
			posting_date=now(),
			save=False,
		)
		jv2.company = company
		jv2.save()
		jv2.submit()

		pcv = self.make_period_closing_voucher()
		surplus_account = pcv.closing_account_head

		expected_gle = (
			("Cost of Goods Sold - TPC", 0.0, 600.0),
			(surplus_account, 600.0, 400.0),
			("Sales - TPC", 400.0, 0.0),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit from `tabGL Entry` where voucher_no=%s order by account
		""",
			(pcv.name),
		)

		self.assertEqual(pcv_gle, expected_gle)

	def test_cost_center_wise_posting(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()

		cost_center1 = create_cost_center("Main")
		cost_center2 = create_cost_center("Western Branch")

		create_sales_invoice(
			company=company,
			cost_center=cost_center1,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
		)
		create_sales_invoice(
			company=company,
			cost_center=cost_center2,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=200,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
		)

		pcv = self.make_period_closing_voucher(submit=False)
		pcv.cost_center_wise_pnl = 1
		pcv.save()
		pcv.submit()
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, cost_center1),
			(surplus_account, 0.0, 200.0, cost_center2),
			("Sales - TPC", 400.0, 0.0, cost_center1),
			("Sales - TPC", 200.0, 0.0, cost_center2),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit, cost_center
			from `tabGL Entry` where voucher_no=%s
			order by account, cost_center
		""",
			(pcv.name),
		)

		self.assertEqual(pcv_gle, expected_gle)

	def test_period_closing_with_finance_book_entries(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")

		si = create_sales_invoice(
			company=company,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			cost_center=cost_center,
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
		)

		jv = make_journal_entry(
			account1="Cash - TPC",
			account2="Sales - TPC",
			amount=400,
			cost_center=cost_center,
			posting_date=now(),
		)
		jv.company = company
		jv.finance_book = create_finance_book().name
		jv.save()
		jv.submit()

		pcv = self.make_period_closing_voucher()
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, None),
			(surplus_account, 0.0, 400.0, jv.finance_book),
			("Sales - TPC", 400.0, 0.0, None),
			("Sales - TPC", 400.0, 0.0, jv.finance_book),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit, finance_book
			from `tabGL Entry` where voucher_no=%s
			order by account, finance_book
		""",
			(pcv.name),
		)

		self.assertEqual(pcv_gle, expected_gle)

	def make_period_closing_voucher(self, submit=True):
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": today(),
				"posting_date": today(),
				"company": "Test PCV Company",
				"fiscal_year": get_fiscal_year(today(), company="Test PCV Company")[0],
				"cost_center": cost_center,
				"closing_account_head": surplus_account,
				"remarks": "test",
			}
		)
		pcv.insert()
		if submit:
			pcv.submit()

		return pcv


def create_company():
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Test PCV Company",
			"country": "United States",
			"default_currency": "USD",
		}
	)
	company.insert(ignore_if_duplicate=True)
	return company.name


def create_account():
	account = frappe.get_doc(
		{
			"account_name": "Reserve and Surplus",
			"is_group": 0,
			"company": "Test PCV Company",
			"root_type": "Liability",
			"report_type": "Balance Sheet",
			"account_currency": "USD",
			"parent_account": "Current Liabilities - TPC",
			"doctype": "Account",
		}
	).insert(ignore_if_duplicate=True)
	return account.name


def create_cost_center(cc_name):
	costcenter = frappe.get_doc(
		{
			"company": "Test PCV Company",
			"cost_center_name": cc_name,
			"doctype": "Cost Center",
			"parent_cost_center": "Test PCV Company - TPC",
		}
	)
	costcenter.insert(ignore_if_duplicate=True)
	return costcenter.name


test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")
