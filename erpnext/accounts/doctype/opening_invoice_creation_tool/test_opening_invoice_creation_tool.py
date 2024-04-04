# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
	create_dimension,
	disable_dimension,
)
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
	get_temporary_opening_account,
)

test_dependencies = ["Customer", "Supplier", "Accounting Dimension"]


class TestOpeningInvoiceCreationTool(FrappeTestCase):
	@classmethod
	def setUpClass(self):
		if not frappe.db.exists("Company", "_Test Opening Invoice Company"):
			make_company()
		create_dimension()
		return super().setUpClass()

	def make_invoices(
		self,
		invoice_type="Sales",
		company=None,
		party_1=None,
		party_2=None,
		invoice_number=None,
		department=None,
	):
		doc = frappe.get_single("Opening Invoice Creation Tool")
		args = get_opening_invoice_creation_dict(
			invoice_type=invoice_type,
			company=company,
			party_1=party_1,
			party_2=party_2,
			invoice_number=invoice_number,
			department=department,
		)
		doc.update(args)
		return doc.make_invoices()

	def test_opening_sales_invoice_creation(self):
		invoices = self.make_invoices(company="_Test Opening Invoice Company")

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["customer", "outstanding_amount", "status"],
			0: ["_Test Customer", 300, "Overdue"],
			1: ["_Test Customer 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value)

		si = frappe.get_doc("Sales Invoice", invoices[0])

		# Check if update stock is not enabled
		self.assertEqual(si.update_stock, 0)

	def check_expected_values(self, invoices, expected_value, invoice_type="Sales"):
		doctype = "Sales Invoice" if invoice_type == "Sales" else "Purchase Invoice"

		for invoice_idx, invoice in enumerate(invoices or []):
			si = frappe.get_doc(doctype, invoice)
			for field_idx, field in enumerate(expected_value["keys"]):
				self.assertEqual(si.get(field, ""), expected_value[invoice_idx][field_idx])

	def test_opening_purchase_invoice_creation(self):
		invoices = self.make_invoices(invoice_type="Purchase", company="_Test Opening Invoice Company")

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["supplier", "outstanding_amount", "status"],
			0: ["_Test Supplier", 300, "Overdue"],
			1: ["_Test Supplier 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value, "Purchase")

	def test_opening_sales_invoice_creation_with_missing_debit_account(self):
		company = "_Test Opening Invoice Company"
		party_1, party_2 = make_customer("Customer A"), make_customer("Customer B")

		old_default_receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
		frappe.db.set_value("Company", company, "default_receivable_account", "")

		if not frappe.db.exists("Cost Center", "_Test Opening Invoice Company - _TOIC"):
			cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "_Test Opening Invoice Company",
					"is_group": 1,
					"company": "_Test Opening Invoice Company",
				}
			)
			cc.insert(ignore_mandatory=True)
			cc2 = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Main",
					"is_group": 0,
					"company": "_Test Opening Invoice Company",
					"parent_cost_center": cc.name,
				}
			)
			cc2.insert()

		frappe.db.set_value("Company", company, "cost_center", "Main - _TOIC")

		self.make_invoices(company="_Test Opening Invoice Company", party_1=party_1, party_2=party_2)

		# Check if missing debit account error raised
		error_log = frappe.db.exists(
			"Error Log",
			{"error": ["like", "%erpnext.controllers.accounts_controller.AccountMissingError%"]},
		)
		self.assertTrue(error_log)

		# teardown
		frappe.db.set_value("Company", company, "default_receivable_account", old_default_receivable_account)

	def test_renaming_of_invoice_using_invoice_number_field(self):
		company = "_Test Opening Invoice Company"
		party_1, party_2 = make_customer("Customer A"), make_customer("Customer B")
		self.make_invoices(
			company=company, party_1=party_1, party_2=party_2, invoice_number="TEST-NEW-INV-11"
		)

		sales_inv1 = frappe.get_all("Sales Invoice", filters={"customer": "Customer A"})[0].get("name")
		sales_inv2 = frappe.get_all("Sales Invoice", filters={"customer": "Customer B"})[0].get("name")
		self.assertEqual(sales_inv1, "TEST-NEW-INV-11")

		# teardown
		for inv in [sales_inv1, sales_inv2]:
			doc = frappe.get_doc("Sales Invoice", inv)
			doc.cancel()

	def test_opening_invoice_with_accounting_dimension(self):
		invoices = self.make_invoices(
			invoice_type="Sales", company="_Test Opening Invoice Company", department="Sales - _TOIC"
		)

		expected_value = {
			"keys": ["customer", "outstanding_amount", "status", "department"],
			0: ["_Test Customer", 300, "Overdue", "Sales - _TOIC"],
			1: ["_Test Customer 1", 250, "Overdue", "Sales - _TOIC"],
		}
		self.check_expected_values(invoices, expected_value, invoice_type="Sales")

	def tearDown(self):
		disable_dimension()


def get_opening_invoice_creation_dict(**args):
	party = "Customer" if args.get("invoice_type", "Sales") == "Sales" else "Supplier"
	company = args.get("company", "_Test Company")

	invoice_dict = frappe._dict(
		{
			"company": company,
			"invoice_type": args.get("invoice_type", "Sales"),
			"invoices": [
				{
					"qty": 1.0,
					"outstanding_amount": 300,
					"party": args.get("party_1") or f"_Test {party}",
					"item_name": "Opening Item",
					"due_date": "2016-09-10",
					"posting_date": "2016-09-05",
					"temporary_opening_account": get_temporary_opening_account(company),
					"invoice_number": args.get("invoice_number"),
				},
				{
					"qty": 2.0,
					"outstanding_amount": 250,
					"party": args.get("party_2") or f"_Test {party} 1",
					"item_name": "Opening Item",
					"due_date": "2016-09-10",
					"posting_date": "2016-09-05",
					"temporary_opening_account": get_temporary_opening_account(company),
					"invoice_number": None,
				},
			],
		}
	)

	invoice_dict.update(args)
	return invoice_dict


def make_company():
	if frappe.db.exists("Company", "_Test Opening Invoice Company"):
		return frappe.get_doc("Company", "_Test Opening Invoice Company")

	company = frappe.new_doc("Company")
	company.company_name = "_Test Opening Invoice Company"
	company.abbr = "_TOIC"
	company.default_currency = "INR"
	company.country = "Pakistan"
	company.insert()
	return company


def make_customer(customer=None):
	customer_name = customer or "Opening Customer"
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_group": "All Customer Groups",
			"customer_type": "Company",
			"territory": "All Territories",
		}
	)

	if not frappe.db.exists("Customer", customer_name):
		customer.insert(ignore_permissions=True)
		return customer.name
	else:
		return frappe.db.exists("Customer", customer_name)
