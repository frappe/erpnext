import unittest

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, getdate, today

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestAccountsReceivable(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabSales Order` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabPayment Entry` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabPayment Ledger Entry` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabJournal Entry` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabExchange Rate Revaluation` where company='_Test Company 2'")

		self.create_usd_account()

	def tearDown(self):
		frappe.db.rollback()

	def create_usd_account(self):
		name = "Debtors USD"
		exists = frappe.db.get_list(
			"Account", filters={"company": "_Test Company 2", "account_name": "Debtors USD"}
		)
		if exists:
			self.debtors_usd = exists[0].name
		else:
			debtors = frappe.get_doc(
				"Account",
				frappe.db.get_list(
					"Account", filters={"company": "_Test Company 2", "account_name": "Debtors"}
				)[0].name,
			)

			debtors_usd = frappe.new_doc("Account")
			debtors_usd.company = debtors.company
			debtors_usd.account_name = "Debtors USD"
			debtors_usd.account_currency = "USD"
			debtors_usd.parent_account = debtors.parent_account
			debtors_usd.account_type = debtors.account_type
			self.debtors_usd = debtors_usd.save().name

	def test_accounts_receivable(self):
		filters = {
			"company": "_Test Company 2",
			"based_on_payment_terms": 1,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		# check invoice grand total and invoiced column's value for 3 payment terms
		name = make_sales_invoice().name
		report = execute(filters)

		expected_data = [[100, 30], [100, 50], [100, 20]]

		for i in range(3):
			row = report[1][i - 1]
			self.assertEqual(expected_data[i - 1], [row.invoice_grand_total, row.invoiced])

		# check invoice grand total, invoiced, paid and outstanding column's value after payment
		make_payment(name)
		report = execute(filters)

		expected_data_after_payment = [[100, 50, 10, 40], [100, 20, 0, 20]]

		for i in range(2):
			row = report[1][i - 1]
			self.assertEqual(
				expected_data_after_payment[i - 1],
				[row.invoice_grand_total, row.invoiced, row.paid, row.outstanding],
			)

		# check invoice grand total, invoiced, paid and outstanding column's value after credit note
		make_credit_note(name)
		report = execute(filters)

		expected_data_after_credit_note = [100, 0, 0, 40, -40, "Debtors - _TC2"]

		row = report[1][0]
		self.assertEqual(
			expected_data_after_credit_note,
			[
				row.invoice_grand_total,
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
				row.party_account,
			],
		)

	def test_payment_againt_po_in_receivable_report(self):
		"""
		Payments made against Purchase Order will show up as outstanding amount
		"""

		so = make_sales_order(
			company="_Test Company 2",
			customer="_Test Customer 2",
			warehouse="Finished Goods - _TC2",
			currency="EUR",
			debit_to="Debtors - _TC2",
			income_account="Sales - _TC2",
			expense_account="Cost of Goods Sold - _TC2",
			cost_center="Main - _TC2",
		)

		pe = get_payment_entry(so.doctype, so.name)
		pe = pe.save().submit()

		filters = {
			"company": "_Test Company 2",
			"based_on_payment_terms": 0,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		report = execute(filters)

		expected_data_after_payment = [0, 1000, 0, -1000]

		row = report[1][0]
		self.assertEqual(
			expected_data_after_payment,
			[
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
			],
		)

	@change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_exchange_revaluation_for_party(self):
		"""
		Exchange Revaluation for party on Receivable/Payable shoule be included
		"""

		company = "_Test Company 2"
		customer = "_Test Customer 2"

		# Using Exchange Gain/Loss account for unrealized as well.
		company_doc = frappe.get_doc("Company", company)
		company_doc.unrealized_exchange_gain_loss_account = company_doc.exchange_gain_loss_account
		company_doc.save()

		si = make_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si.currency = "USD"
		si.conversion_rate = 0.90
		si.debit_to = self.debtors_usd
		si = si.save().submit()

		# Exchange Revaluation
		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = company
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)
		err.accounts[0].new_exchange_rate = 0.95
		row = err.accounts[0]
		row.new_balance_in_base_currency = flt(
			row.new_exchange_rate * flt(row.balance_in_account_currency)
		)
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		# Submit JV for ERR
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()

		filters = {
			"company": company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}
		report = execute(filters)

		expected_data_for_err = [0, -5, 0, 5]
		row = [x for x in report[1] if x.voucher_type == je.doctype and x.voucher_no == je.name][0]
		self.assertEqual(
			expected_data_for_err,
			[
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
			],
		)


def make_sales_invoice(no_payment_schedule=False, do_not_submit=False):
	frappe.set_user("Administrator")

	si = create_sales_invoice(
		company="_Test Company 2",
		customer="_Test Customer 2",
		currency="EUR",
		warehouse="Finished Goods - _TC2",
		debit_to="Debtors - _TC2",
		income_account="Sales - _TC2",
		expense_account="Cost of Goods Sold - _TC2",
		cost_center="Main - _TC2",
		do_not_save=1,
	)

	if not no_payment_schedule:
		si.append(
			"payment_schedule",
			dict(due_date=getdate(add_days(today(), 30)), invoice_portion=30.00, payment_amount=30),
		)
		si.append(
			"payment_schedule",
			dict(due_date=getdate(add_days(today(), 60)), invoice_portion=50.00, payment_amount=50),
		)
		si.append(
			"payment_schedule",
			dict(due_date=getdate(add_days(today(), 90)), invoice_portion=20.00, payment_amount=20),
		)

	si = si.save()

	if not do_not_submit:
		si = si.submit()

	return si


def make_payment(docname):
	pe = get_payment_entry("Sales Invoice", docname, bank_account="Cash - _TC2", party_amount=40)
	pe.paid_from = "Debtors - _TC2"
	pe.insert()
	pe.submit()


def make_credit_note(docname):
	create_sales_invoice(
		company="_Test Company 2",
		customer="_Test Customer 2",
		currency="EUR",
		qty=-1,
		warehouse="Finished Goods - _TC2",
		debit_to="Debtors - _TC2",
		income_account="Sales - _TC2",
		expense_account="Cost of Goods Sold - _TC2",
		cost_center="Main - _TC2",
		is_return=1,
		return_against=docname,
	)
