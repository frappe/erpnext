# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.regional.report.irs_1099.irs_1099 import execute as execute_1099_report
from erpnext.tests.utils import ERPNextTestSuite


class TestUnitedStates(ERPNextTestSuite):
	def test_irs_1099_custom_field(self):
		if not frappe.db.exists("Supplier", "_US 1099 Test Supplier"):
			make_irs_1099_supplier()
			supplier = frappe.get_doc("Supplier", "_US 1099 Test Supplier")
			self.assertEqual(supplier.irs_1099, 1)

	def test_irs_1099_report(self):
		make_irs_1099_supplier()
		make_payment_entry_to_irs_1099_supplier()
		filters = frappe._dict({"fiscal_year": "_Test Fiscal Year 2016", "company": "_Test Company 1"})
		columns, data = execute_1099_report(filters)
		expected_row = {
			"supplier": "_US 1099 Test Supplier",
			"supplier_group": "Services",
			"payments": 100.0,
			"tax_id": "04-1234567",
		}
		self.assertEqual(data[0], expected_row)


def make_irs_1099_supplier():
	doc = frappe.new_doc("Supplier")
	doc.supplier_name = "_US 1099 Test Supplier"
	doc.supplier_group = "Services"
	doc.supplier_type = "Company"
	doc.country = "United States"
	doc.tax_id = "04-1234567"
	doc.irs_1099 = 1
	doc.save()
	return doc


def make_payment_entry_to_irs_1099_supplier():
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Pay"
	pe.company = "_Test Company 1"
	pe.posting_date = "2016-01-10"
	pe.paid_from = "_Test Bank USD - _TC1"
	pe.paid_to = "_Test Payable USD - _TC1"
	pe.paid_amount = 100
	pe.received_amount = 100
	pe.reference_no = "For IRS 1099 testing"
	pe.reference_date = "2016-01-10"
	pe.party_type = "Supplier"
	pe.party = "_US 1099 Test Supplier"
	pe.insert()
	pe.submit()
