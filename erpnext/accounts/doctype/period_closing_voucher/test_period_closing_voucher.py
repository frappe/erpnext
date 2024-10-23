# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.finance_book.test_finance_book import create_finance_book
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import get_fiscal_year


class TestPeriodClosingVoucher(unittest.TestCase):
	def test_closing_entry(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			save=False,
		)
		jv1.company = company
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=600,
			account1="Cost of Goods Sold - TPC",
			account2="Cash - TPC",
			cost_center=cost_center,
			save=False,
		)
		jv2.company = company
		jv2.save()
		jv2.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		surplus_account = pcv.closing_account_head

		expected_gle = (
			("Cost of Goods Sold - TPC", 0.0, 600.0),
			(surplus_account, 200.0, 0.0),
			("Sales - TPC", 400.0, 0.0),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit from `tabGL Entry` where voucher_no=%s order by account
		""",
			(pcv.name),
		)
		pcv.reload()
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertEqual(pcv_gle, expected_gle)

	def test_cost_center_wise_posting(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

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
			posting_date="2021-03-15",
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
			posting_date="2021-03-15",
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
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

		self.assertSequenceEqual(pcv_gle, expected_gle)

		pcv.reload()
		pcv.cancel()

		self.assertFalse(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Period Closing Voucher", "voucher_no": pcv.name, "is_cancelled": 0},
			)
		)

	def test_period_closing_with_finance_book_entries(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")

		create_sales_invoice(
			company=company,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			cost_center=cost_center,
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)

		jv = make_journal_entry(
			account1="Cash - TPC",
			account2="Sales - TPC",
			amount=400,
			cost_center=cost_center,
			posting_date="2021-03-15",
		)
		jv.company = company
		jv.finance_book = create_finance_book().name
		jv.save()
		jv.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
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

		self.assertSequenceEqual(pcv_gle, expected_gle)

	def test_gl_entries_restrictions(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		self.make_period_closing_voucher(posting_date="2021-03-31")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			save=False,
		)
		jv1.company = company
		jv1.save()

		self.assertRaises(frappe.ValidationError, jv1.submit)

	def test_closing_balance_with_dimensions_and_test_reposting_entry(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabAccount Closing Balance` where company='Test PCV Company'")

		company = create_company()
		cost_center1 = create_cost_center("Test Cost Center 1")
		cost_center2 = create_cost_center("Test Cost Center 2")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center1,
			save=False,
		)
		jv1.company = company
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=200,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			save=False,
		)
		jv2.company = company
		jv2.save()
		jv2.submit()

		pcv1 = self.make_period_closing_voucher(posting_date="2021-03-31")

		closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv1.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(closing_balance.credit, 400)
		self.assertEqual(closing_balance.credit_in_account_currency, 400)

		jv3 = make_journal_entry(
			posting_date="2022-03-15",
			amount=300,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			save=False,
		)

		jv3.company = company
		jv3.save()
		jv3.submit()

		pcv2 = self.make_period_closing_voucher(posting_date="2022-03-31")

		cc1_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		cc2_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center2,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(cc1_closing_balance.credit, 400)
		self.assertEqual(cc1_closing_balance.credit_in_account_currency, 400)
		self.assertEqual(cc2_closing_balance.credit, 500)
		self.assertEqual(cc2_closing_balance.credit_in_account_currency, 500)

		warehouse = frappe.db.get_value("Warehouse", {"company": company}, "name")

		repost_doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"company": company,
				"posting_date": "2020-03-15",
				"based_on": "Item and Warehouse",
				"item_code": "Test Item 1",
				"warehouse": warehouse,
			}
		)

		self.assertRaises(frappe.ValidationError, repost_doc.save)

		repost_doc.posting_date = today()
		repost_doc.save()

	def make_period_closing_voucher(self, posting_date, submit=True):
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")
		fy = get_fiscal_year(posting_date, company="Test PCV Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": posting_date or today(),
				"period_start_date": fy[1],
				"period_end_date": fy[2],
				"company": "Test PCV Company",
				"fiscal_year": fy[0],
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
