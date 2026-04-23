# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_to_date, today

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
	create_purchase_invoice,
	create_records,
	create_sales_invoice,
	create_tax_withholding_category,
	make_journal_entry_with_tax_withholding,
)
from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestTaxWithholdingDetails(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.clear_old_entries()
		create_records()

	def test_tax_withholding_for_customers(self):
		create_tax_category(cumulative_threshold=300)
		frappe.db.set_value("Customer", "Test TCS Customer", "tax_withholding_category", "TCS")
		si = create_sales_invoice(customer="Test TCS Customer", rate=1000)
		si.submit()

		create_tcs_payment_entry()
		jv = create_tcs_journal_entry()

		filters = frappe._dict(
			company="_Test Company", party_type="Customer", from_date=today(), to_date=today()
		)
		result = execute(filters)[1]

		expected_values = [
			[jv.name, "TCS", 0.075, 1000.75, 0.75, 1000.75],
			["", "TCS", 0.075, None, 0.75, None],
			[si.name, "TCS", 0.075, 1000.0, 0.75, 1000.75],
		]
		self.check_expected_values(result, expected_values)

	def test_single_account_for_multiple_categories(self):
		create_tax_category("TDS - 1", rate=10, account="TDS - _TC", cumulative_threshold=1)
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", "TDS - 1")
		inv_1 = create_purchase_invoice(supplier="Test TDS Supplier", rate=5000)
		inv_1.submit()

		create_tax_category("TDS - 2", rate=20, account="TDS - _TC", cumulative_threshold=1)
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", "TDS - 2")
		inv_2 = create_purchase_invoice(supplier="Test TDS Supplier", rate=5000)
		inv_2.submit()
		result = execute(
			frappe._dict(company="_Test Company", party_type="Supplier", from_date=today(), to_date=today())
		)[1]
		expected_values = [
			[inv_1.name, "TDS - 1", 10, 5000, 500, 4500],
			[inv_2.name, "TDS - 2", 20, 5000, 1000, 4000],
		]
		self.check_expected_values(result, expected_values)

	def test_date_filters_in_multiple_tax_withholding_rules(self):
		create_tax_category("TDS - 3", rate=10, account="TDS - _TC", cumulative_threshold=1)
		# insert new rate in same fiscal year
		fiscal_year = get_fiscal_year(today(), company="_Test Company")
		mid_year = add_to_date(fiscal_year[1], months=6)
		tds_doc = frappe.get_doc("Tax Withholding Category", "TDS - 3")
		tds_doc.rates[0].to_date = mid_year
		from_date = add_to_date(mid_year, days=1)
		tds_doc.append(
			"rates",
			{
				"tax_withholding_rate": 20,
				"from_date": from_date,
				"to_date": fiscal_year[2],
				"single_threshold": 1,
				"cumulative_threshold": 1,
			},
		)

		tds_doc.save()

		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", tds_doc.name)
		inv_1 = create_purchase_invoice(
			supplier="Test TDS Supplier",
			rate=5000,
			posting_date=add_to_date(fiscal_year[1], days=1),
			set_posting_time=True,
		)
		inv_1.submit()

		inv_2 = create_purchase_invoice(
			supplier="Test TDS Supplier",
			rate=5000,
			posting_date=from_date,
			set_posting_time=True,
		)
		inv_2.submit()

		result = execute(
			frappe._dict(
				company="_Test Company",
				party_type="Supplier",
				from_date=fiscal_year[1],
				to_date=fiscal_year[2],
			)
		)[1]

		expected_values = [
			[inv_1.name, "TDS - 3", 10.0, 5000, 500, 4500],
			[inv_2.name, "TDS - 3", 20.0, 5000, 1000, 4000],
		]
		self.check_expected_values(result, expected_values)

	def check_expected_values(self, result, expected_values):
		self.assertEqual(len(result), len(expected_values))
		for i in range(len(result)):
			voucher = frappe._dict(result[i])
			voucher_expected_values = expected_values[i]
			voucher_actual_values = (
				voucher.ref_no,
				voucher.tax_withholding_category,
				voucher.rate,
				voucher.base_total,
				voucher.tax_amount,
				voucher.grand_total,
			)
			self.assertSequenceEqual(voucher_actual_values, voucher_expected_values)


def create_tax_category(category="TCS", rate=0.075, account="TCS - _TC", cumulative_threshold=0):
	fiscal_year = get_fiscal_year(today(), company="_Test Company")
	from_date = fiscal_year[1]
	to_date = fiscal_year[2]

	create_tax_withholding_category(
		category_name=category,
		rate=rate,
		from_date=from_date,
		to_date=to_date,
		account=account,
		cumulative_threshold=cumulative_threshold,
	)


def create_tcs_payment_entry(party="Test TCS Customer", category="TCS", amount=1000):
	"""Create a TCS Payment Entry that generates a Tax Withholding Entry (Over Withheld)."""
	payment_entry = create_payment_entry(
		payment_type="Receive",
		party_type="Customer",
		party=party,
		paid_from="Debtors - _TC",
		paid_to="Cash - _TC",
		paid_amount=amount,
	)
	payment_entry.apply_tds = 1
	payment_entry.tax_withholding_category = category
	payment_entry.save()
	payment_entry.submit()
	return payment_entry


def create_tcs_journal_entry(party="Test TCS Customer", category="TCS", amount=1000):
	"""Create a TCS Credit Note Journal Entry that generates a Tax Withholding Entry."""
	jv = make_journal_entry_with_tax_withholding(
		party_type="Customer",
		party=party,
		voucher_type="Credit Note",
		amount=amount,
		save=False,
	)
	jv.apply_tds = 1
	jv.tax_withholding_category = category
	jv.save()
	jv.submit()
	return jv
