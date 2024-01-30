# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
	create_tax_withholding_category,
)
from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year


class TestTaxWithholdingDetails(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.clear_old_entries()
		create_tax_accounts()
		create_tcs_category()

	def test_tax_withholding_for_customers(self):
		si = create_sales_invoice(rate=1000)
		pe = create_tcs_payment_entry()
		jv = create_tcs_journal_entry()

		filters = frappe._dict(
			company="_Test Company", party_type="Customer", from_date=today(), to_date=today()
		)
		result = execute(filters)[1]
		expected_values = [
			# Check for JV totals using back calculation logic
			[jv.name, "TCS", 0.075, -10000.0, -7.5, -10000.0],
			[pe.name, "TCS", 0.075, 2550, 0.53, 2550.53],
			[si.name, "TCS", 0.075, 1000, 0.525, 1000.525],
		]
		self.check_expected_values(result, expected_values)

	def check_expected_values(self, result, expected_values):
		for i in range(len(result)):
			voucher = frappe._dict(result[i])
			voucher_expected_values = expected_values[i]
			voucher_actual_values = (
				voucher.ref_no,
				voucher.section_code,
				voucher.rate,
				voucher.base_total,
				voucher.tax_amount,
				voucher.grand_total,
			)
			self.assertSequenceEqual(voucher_actual_values, voucher_expected_values)

	def tearDown(self):
		self.clear_old_entries()


def create_tax_accounts():
	account_names = ["TCS", "TDS"]
	for account in account_names:
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": "_Test Company",
				"account_name": account,
				"parent_account": "Duties and Taxes - _TC",
				"report_type": "Balance Sheet",
				"root_type": "Liability",
			}
		).insert(ignore_if_duplicate=True)


def create_tcs_category():
	fiscal_year = get_fiscal_year(today(), company="_Test Company")
	from_date = fiscal_year[1]
	to_date = fiscal_year[2]

	tax_category = create_tax_withholding_category(
		category_name="TCS",
		rate=0.075,
		from_date=from_date,
		to_date=to_date,
		account="TCS - _TC",
		cumulative_threshold=300,
	)

	customer = frappe.get_doc("Customer", "_Test Customer")
	customer.tax_withholding_category = "TCS"
	customer.save()


def create_tcs_payment_entry():
	payment_entry = create_payment_entry(
		payment_type="Receive",
		party_type="Customer",
		party="_Test Customer",
		paid_from="Debtors - _TC",
		paid_to="Cash - _TC",
		paid_amount=2550,
	)

	payment_entry.append(
		"taxes",
		{
			"account_head": "TCS - _TC",
			"charge_type": "Actual",
			"tax_amount": 0.53,
			"add_deduct_tax": "Add",
			"description": "Test",
			"cost_center": "Main - _TC",
		},
	)
	payment_entry.submit()
	return payment_entry


def create_tcs_journal_entry():
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = today()
	jv.company = "_Test Company"
	jv.set(
		"accounts",
		[
			{
				"account": "Debtors - _TC",
				"party_type": "Customer",
				"party": "_Test Customer",
				"credit_in_account_currency": 10000,
			},
			{
				"account": "Debtors - _TC",
				"party_type": "Customer",
				"party": "_Test Customer",
				"debit_in_account_currency": 9992.5,
			},
			{
				"account": "TCS - _TC",
				"debit_in_account_currency": 7.5,
			},
		],
	)
	jv.insert()
	return jv.submit()
