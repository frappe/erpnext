import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
	Deferred_Revenue_and_Expense_Report,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year


class TestDeferredRevenueAndExpense(FrappeTestCase, AccountsTestMixin):
	@classmethod
	def setUpClass(self):
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

	def setup_deferred_accounts_and_items(self):
		# created deferred expense accounts, if not found
		self.deferred_revenue_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - " + self.company_abbr,
			company=self.company,
		)

		# created deferred expense accounts, if not found
		self.deferred_expense_account = create_account(
			account_name="Deferred Expense",
			parent_account="Current Assets - " + self.company_abbr,
			company=self.company,
		)

	def setUp(self):
		self.create_company()
		self.create_customer("_Test Customer")
		self.create_supplier("_Test Furniture Supplier")
		self.setup_deferred_accounts_and_items()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_deferred_revenue(self):
		self.create_item("_Test Internet Subscription", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_revenue = 1
		item.item_defaults[0].deferred_revenue_account = self.deferred_revenue_account
		item.no_of_months = 3
		item.save()

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date="2021-05-01",
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].income_account = self.income_account
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2021-05-01"
		si.items[0].service_end_date = "2021-08-01"
		si.items[0].deferred_revenue_account = self.deferred_revenue_account
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
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

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_deferred_expense(self):
		self.create_item("_Test Office Desk", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = self.deferred_expense_account
		item.no_of_months_exp = 3
		item.save()

		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
			warehouse=self.warehouse,
			qty=1,
		)
		pi.set_posting_time = True
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2021-05-01"
		pi.items[0].service_end_date = "2021-08-01"
		pi.items[0].deferred_expense_account = self.deferred_expense_account
		pi.items[0].expense_account = self.expense_account
		pi.save()
		pi.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Expense",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
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

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_zero_months(self):
		self.create_item("_Test Internet Subscription", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = self.deferred_revenue_account
		item.no_of_months = 0
		item.save()

		si = create_sales_invoice(
			item=item.name,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date="2021-05-01",
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].enable_deferred_revenue = 1
		si.items[0].income_account = self.income_account
		si.items[0].deferred_revenue_account = self.deferred_revenue_account
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
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

	@change_settings(
		"Accounts Settings",
		{"book_deferred_entries_based_on": "Months", "book_deferred_entries_via_journal_entry": 0},
	)
	def test_zero_amount(self):
		self.create_item("_Test Office Desk", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = self.deferred_expense_account
		item.no_of_months_exp = 12
		item.save()

		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 12, 30),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=3910,
			price_list_rate=3910,
			warehouse=self.warehouse,
			qty=1,
		)
		pi.set_posting_time = True
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2021-12-30"
		pi.items[0].service_end_date = "2022-12-30"
		pi.items[0].deferred_expense_account = self.deferred_expense_account
		pi.items[0].expense_account = self.expense_account
		pi.save()
		pi.submit()

		pda = frappe.get_doc(
			doctype="Process Deferred Accounting",
			posting_date=nowdate(),
			start_date="2022-01-01",
			end_date="2022-01-31",
			type="Expense",
			company=self.company,
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2022-01-31"))
		self.filters = frappe._dict(
			{
				"company": self.company,
				"filter_based_on": "Date Range",
				"period_start_date": "2022-01-01",
				"period_end_date": "2022-01-31",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Expense",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()

		# fetch the invoice from deferred invoices list
		inv = [d for d in report.deferred_invoices if d.name == pi.name]
		# make sure the list isn't empty
		self.assertTrue(inv)
		# calculate the total deferred expense for the period
		inv = inv[0].calculate_invoice_revenue_expense_for_period()
		deferred_exp = sum([inv[idx].actual for idx in range(len(report.period_list))])
		# make sure the total deferred expense is greater than 0
		self.assertLess(deferred_exp, 0)
