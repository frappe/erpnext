import unittest

import frappe
from frappe import qb
from frappe.utils import nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
	Deferred_Revenue_and_Expense_Report,
)
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.stock.doctype.item.test_item import create_item


class TestDeferredRevenueAndExpense(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		clear_accounts_and_items()
		create_company()
		self.maxDiff = None

	def clear_old_entries(self):
		sinv = qb.DocType("Sales Invoice")
		sinv_item = qb.DocType("Sales Invoice Item")
		pinv = qb.DocType("Purchase Invoice")
		pinv_item = qb.DocType("Purchase Invoice Item")

		# delete existing invoices with deferred items
		deferred_invoices = (
			qb.from_(sinv)
			.join(sinv_item)
			.on(sinv.name == sinv_item.parent)
			.select(sinv.name)
			.where(sinv_item.enable_deferred_revenue == 1)
			.run()
		)
		if deferred_invoices:
			qb.from_(sinv).delete().where(sinv.name.isin(deferred_invoices)).run()

		deferred_invoices = (
			qb.from_(pinv)
			.join(pinv_item)
			.on(pinv.name == pinv_item.parent)
			.select(pinv.name)
			.where(pinv_item.enable_deferred_expense == 1)
			.run()
		)
		if deferred_invoices:
			qb.from_(pinv).delete().where(pinv.name.isin(deferred_invoices)).run()

	def test_deferred_revenue(self):
		self.clear_old_entries()

		# created deferred expense accounts, if not found
		deferred_revenue_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _CD",
			company="_Test Company DR",
		)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_based_on = "Months"
		acc_settings.save()

		customer = frappe.new_doc("Customer")
		customer.customer_name = "_Test Customer DR"
		customer.type = "Individual"
		customer.insert()

		item = create_item(
			"_Test Internet Subscription",
			is_stock_item=0,
			warehouse="All Warehouses - _CD",
			company="_Test Company DR",
		)
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_revenue_account
		item.no_of_months = 3
		item.save()

		si = create_sales_invoice(
			item=item.name,
			company="_Test Company DR",
			customer="_Test Customer DR",
			debit_to="Debtors - _CD",
			posting_date="2021-05-01",
			parent_cost_center="Main - _CD",
			cost_center="Main - _CD",
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].income_account = "Sales - _CD"
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2021-05-01"
		si.items[0].service_end_date = "2021-08-01"
		si.items[0].deferred_revenue_account = deferred_revenue_account
		si.items[0].income_account = "Sales - _CD"
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company="_Test Company DR",
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", frappe.defaults.get_user_default("fiscal_year"))
		self.filters = frappe._dict(
			{
				"company": frappe.defaults.get_user_default("Company"),
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Revenue",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": 100.0, "actual": 100.0},
			{"key": "jun_2021", "total": 100.0, "actual": 100.0},
			{"key": "jul_2021", "total": 100.0, "actual": 100.0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)

	def test_deferred_expense(self):
		self.clear_old_entries()

		# created deferred expense accounts, if not found
		deferred_expense_account = create_account(
			account_name="Deferred Expense",
			parent_account="Current Assets - _CD",
			company="_Test Company DR",
		)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_based_on = "Months"
		acc_settings.save()

		supplier = create_supplier(
			supplier_name="_Test Furniture Supplier", supplier_group="Local", supplier_type="Company"
		)
		supplier.save()

		item = create_item(
			"_Test Office Desk",
			is_stock_item=0,
			warehouse="All Warehouses - _CD",
			company="_Test Company DR",
		)
		item.enable_deferred_expense = 1
		item.deferred_expense_account = deferred_expense_account
		item.no_of_months_exp = 3
		item.save()

		pi = make_purchase_invoice(
			item=item.name,
			company="_Test Company DR",
			supplier="_Test Furniture Supplier",
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			parent_cost_center="Main - _CD",
			cost_center="Main - _CD",
			do_not_save=True,
			rate=300,
			price_list_rate=300,
			warehouse="All Warehouses - _CD",
			qty=1,
		)
		pi.set_posting_time = True
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2021-05-01"
		pi.items[0].service_end_date = "2021-08-01"
		pi.items[0].deferred_expense_account = deferred_expense_account
		pi.items[0].expense_account = "Office Maintenance Expenses - _CD"
		pi.save()
		pi.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Expense",
				company="_Test Company DR",
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", frappe.defaults.get_user_default("fiscal_year"))
		self.filters = frappe._dict(
			{
				"company": frappe.defaults.get_user_default("Company"),
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Expense",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": -100.0, "actual": -100.0},
			{"key": "jun_2021", "total": -100.0, "actual": -100.0},
			{"key": "jul_2021", "total": -100.0, "actual": -100.0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)

	def test_zero_months(self):
		self.clear_old_entries()
		# created deferred expense accounts, if not found
		deferred_revenue_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _CD",
			company="_Test Company DR",
		)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_based_on = "Months"
		acc_settings.save()

		customer = frappe.new_doc("Customer")
		customer.customer_name = "_Test Customer DR"
		customer.type = "Individual"
		customer.insert()

		item = create_item(
			"_Test Internet Subscription",
			is_stock_item=0,
			warehouse="All Warehouses - _CD",
			company="_Test Company DR",
		)
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_revenue_account
		item.no_of_months = 0
		item.save()

		si = create_sales_invoice(
			item=item.name,
			company="_Test Company DR",
			customer="_Test Customer DR",
			debit_to="Debtors - _CD",
			posting_date="2021-05-01",
			parent_cost_center="Main - _CD",
			cost_center="Main - _CD",
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].enable_deferred_revenue = 1
		si.items[0].income_account = "Sales - _CD"
		si.items[0].deferred_revenue_account = deferred_revenue_account
		si.items[0].income_account = "Sales - _CD"
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company="_Test Company DR",
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", frappe.defaults.get_user_default("fiscal_year"))
		self.filters = frappe._dict(
			{
				"company": frappe.defaults.get_user_default("Company"),
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Revenue",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": 300.0, "actual": 300.0},
			{"key": "jun_2021", "total": 0, "actual": 0},
			{"key": "jul_2021", "total": 0, "actual": 0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)


def create_company():
	company = frappe.db.exists("Company", "_Test Company DR")
	if not company:
		company = frappe.new_doc("Company")
		company.company_name = "_Test Company DR"
		company.default_currency = "INR"
		company.chart_of_accounts = "Standard"
		company.insert()


def clear_accounts_and_items():
	item = qb.DocType("Item")
	account = qb.DocType("Account")
	customer = qb.DocType("Customer")
	supplier = qb.DocType("Supplier")

	qb.from_(account).delete().where(
		(account.account_name == "Deferred Revenue")
		| (account.account_name == "Deferred Expense") & (account.company == "_Test Company DR")
	).run()
	qb.from_(item).delete().where(
		(item.item_code == "_Test Internet Subscription") | (item.item_code == "_Test Office Rent")
	).run()
	qb.from_(customer).delete().where(customer.customer_name == "_Test Customer DR").run()
	qb.from_(supplier).delete().where(supplier.supplier_name == "_Test Furniture Supplier").run()
