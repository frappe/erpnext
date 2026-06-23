# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
	get_temporary_opening_account,
)
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.tests.utils import ERPNextTestSuite


class TestOpeningInvoiceCreationTool(ERPNextTestSuite):
	def make_invoices(
		self,
		invoice_type="Sales",
		company=None,
		invoices=None,
		project=None,
		cost_center=None,
		department=None,
		return_doc=False,
	):
		doc = frappe.get_single("Opening Invoice Creation Tool")
		args = get_opening_invoice_creation_dict(
			invoice_type=invoice_type,
			company=company,
			invoices=invoices,
			project=project,
			cost_center=cost_center,
			department=department,
		)
		doc.update(args)

		if return_doc:
			return doc

		return doc.make_invoices()

	def test_opening_sales_invoice_creation(self):
		invoices = self.make_invoices(company="_Test Opening Invoice Company")

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["customer", "outstanding_amount", "status"],
			0: ["_Test Customer", 200, "Overdue"],
			1: ["_Test Customer 1", 200, "Overdue"],
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

	def test_opening_invoice_requires_temporary_account_type(self):
		doc = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		doc.invoices[0].temporary_opening_account = "Sales - _TOIC"
		self.assertRaises(frappe.ValidationError, doc.make_invoices)

	def test_opening_purchase_invoice_creation(self):
		invoices = self.make_invoices(invoice_type="Purchase", company="_Test Opening Invoice Company")

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["supplier", "outstanding_amount", "status"],
			0: ["_Test Supplier", 200, "Overdue"],
			1: ["_Test Supplier 1", 200, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value, "Purchase")

	def test_opening_sales_invoice_creation_with_missing_debit_account(self):
		party_1, party_2 = make_customer("Customer A"), make_customer("Customer B")

		old_default_receivable_account = frappe.db.get_value(
			"Company", "_Test Opening Invoice Company", "default_receivable_account"
		)
		frappe.db.set_value("Company", "_Test Opening Invoice Company", "default_receivable_account", "")

		self.make_invoices(
			company="_Test Opening Invoice Company",
			invoices=[{"party": party_1}, {"party": party_2}],
		)

		# Check if missing debit account error raised
		error_log = frappe.db.exists(
			"Error Log",
			{"error": ["like", "%erpnext.controllers.accounts_controller.AccountMissingError%"]},
		)
		self.assertTrue(error_log)

		# teardown
		frappe.db.set_value(
			"Company",
			"_Test Opening Invoice Company",
			"default_receivable_account",
			old_default_receivable_account,
		)

	def test_renaming_of_invoice_using_invoice_number_field(self):
		party_1, party_2 = make_customer("Customer A"), make_customer("Customer B")
		invoices = self.make_invoices(
			company="_Test Opening Invoice Company",
			invoices=[
				{"party": party_1, "invoice_number": "TEST-NEW-INV-11"},
				{"party": party_2},
			],
		)

		self.assertEqual(invoices[0], "TEST-NEW-INV-11")

	def test_opening_invoice_with_accounting_dimension(self):
		invoices = self.make_invoices(
			invoice_type="Sales", company="_Test Opening Invoice Company", department="Sales - _TOIC"
		)

		for invoice in invoices:
			self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "department"), "Sales - _TOIC")

	def test_opening_entry_project_linking(self):
		doc = self.make_invoices(
			company="_Test Opening Invoice Company", invoice_type="Sales", return_doc=True
		)
		project_1 = make_project(
			{"project_name": "Test Opening Invoice projecty 01", "company": "_Test Opening Invoice Company"}
		)
		project_2 = make_project(
			{"project_name": "Test Opening Invoice projecty 02", "company": "_Test Opening Invoice Company"}
		)
		doc.invoices[0].project = project_1.name
		doc.invoices[1].project = project_2.name
		invoices = doc.make_invoices()
		sales_invoice_1 = frappe.get_doc("Sales Invoice", invoices[0])
		sales_invoice_2 = frappe.get_doc("Sales Invoice", invoices[1])

		self.assertEqual(sales_invoice_1.items[0].project, project_1.name)
		self.assertEqual(sales_invoice_2.items[0].project, project_2.name)


def get_opening_invoice_creation_dict(**args):
	party = "Customer" if args.get("invoice_type", "Sales") == "Sales" else "Supplier"
	company = args.get("company", "_Test Company")
	default_invoices = []
	default_invoice_rows = [
		{
			"qty": 1.0,
			"outstanding_amount": 200,
			"party": f"_Test {party}",
			"item_name": "Opening Item",
			"due_date": add_days(today(), -10),
			"posting_date": add_days(today(), -15),
			"temporary_opening_account": get_temporary_opening_account(company),
		},
		{
			"qty": 1.0,
			"outstanding_amount": 200,
			"party": f"_Test {party} 1",
			"item_name": "Opening Item",
			"due_date": add_days(today(), -10),
			"posting_date": add_days(today(), -15),
			"temporary_opening_account": get_temporary_opening_account(company),
		},
	]

	for row in args.get("invoices") or default_invoice_rows:
		default_invoices.append(
			{
				"qty": row.get("qty") or 1.0,
				"outstanding_amount": row.get("outstanding_amount") or 200,
				"party": row.get("party") or f"_Test {party}",
				"item_name": row.get("item_name") or "Opening Item",
				"due_date": row.get("due_date") or add_days(today(), -10),
				"posting_date": row.get("posting_date") or add_days(today(), -15),
				"temporary_opening_account": row.get("temporary_opening_account")
				or get_temporary_opening_account(company),
				"invoice_number": row.get("invoice_number"),
				"project": row.get("project"),
				"cost_center": row.get("cost_center"),
			}
		)

	invoice_dict = frappe._dict(
		{
			"company": company,
			"invoice_type": args.get("invoice_type", "Sales"),
			"project": args.get("project"),
			"cost_center": args.get("cost_center"),
			"invoices": default_invoices,
		}
	)

	invoice_dict.update(args)
	invoice_dict.invoices = default_invoices
	return invoice_dict


def make_customer(customer=None):
	customer_name = customer or "Opening Customer"
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_group": "Individual",
			"customer_type": "Company",
			"territory": "All Territories",
		}
	)

	if not frappe.db.exists("Customer", customer_name):
		customer.insert(ignore_permissions=True)
		return customer.name
	else:
		return frappe.db.exists("Customer", customer_name)
