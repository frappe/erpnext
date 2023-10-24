# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
	create_tax_withholding_category,
)
from erpnext.accounts.report.tds_payable_monthly.tds_payable_monthly import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year


class TestTdsPayableMonthly(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.clear_old_entries()
		create_tax_accounts()
		create_tcs_category()

	def test_tax_withholding_for_customers(self):
		si = create_sales_invoice(rate=1000)
		pe = create_tcs_payment_entry()
		filters = frappe._dict(
			company="_Test Company", party_type="Customer", from_date=today(), to_date=today()
		)
		result = execute(filters)[1]
		expected_values = [
			[pe.name, "TCS", 0.075, 2550, 0.53, 2550.53],
			[si.name, "TCS", 0.075, 1000, 0.53, 1000.53],
		]
		self.check_expected_values(result, expected_values)

	def check_expected_values(self, result, expected_values):
		for i in range(len(result)):
			voucher = frappe._dict(result[i])
			voucher_expected_values = expected_values[i]
			self.assertEqual(voucher.ref_no, voucher_expected_values[0])
			self.assertEqual(voucher.section_code, voucher_expected_values[1])
			self.assertEqual(voucher.rate, voucher_expected_values[2])
			self.assertEqual(voucher.base_total, voucher_expected_values[3])
			self.assertEqual(voucher.tax_amount, voucher_expected_values[4])
			self.assertEqual(voucher.grand_total, voucher_expected_values[5])

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
