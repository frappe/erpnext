# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
	create_and_start_import,
	get_temporary_opening_account,
)
from erpnext.accounts.doctype.tax_rule.test_tax_rule import make_tax_rule
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
		args = get_opening_invoice_creation_dict(
			invoice_type=invoice_type,
			company=company,
			invoices=invoices,
			project=project,
			cost_center=cost_center,
			department=department,
		)
		doc = frappe.get_doc({"doctype": "Opening Invoice Creation Tool", **args})
		doc.insert()

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

	def test_import_run_keeps_results(self):
		doc = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		doc.make_invoices()

		doc.reload()
		self.assertEqual(doc.status, "Success")
		self.assertEqual(doc.get_import_result_summary(), {"total": 2, "successes": 2, "failures": 0})
		logs = frappe.get_all(
			"Opening Invoice Creation Log",
			filters={"opening_invoice_creation_tool": doc.name},
			fields=["success", "reference_name"],
		)
		self.assertEqual(len(logs), 2)
		self.assertTrue(all(log.success and log.reference_name for log in logs))

	def test_create_missing_party_before_run_is_saved(self):
		party = "New Opening Customer"
		frappe.delete_doc_if_exists("Customer", party, force=True)
		args = get_opening_invoice_creation_dict(
			company="_Test Opening Invoice Company",
			invoices=[{"party": party}],
		)
		args.create_missing_party = 1

		result = create_and_start_import(frappe.as_json({"doctype": "Opening Invoice Creation Tool", **args}))
		run = frappe.get_doc("Opening Invoice Creation Tool", result["name"])

		self.assertTrue(frappe.db.exists("Customer", party))
		self.assertEqual(run.status, "Success")
		self.assertEqual(len(result["invoices"]), 1)

	def test_started_run_cannot_start_again(self):
		doc = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		doc.make_invoices()
		doc.reload()
		self.assertRaises(frappe.ValidationError, doc.make_invoices)

	def check_expected_values(self, invoices, expected_value, invoice_type="Sales"):
		doctype = "Sales Invoice" if invoice_type == "Sales" else "Purchase Invoice"

		for invoice_idx, invoice in enumerate(invoices or []):
			si = frappe.get_doc(doctype, invoice)
			for field_idx, field in enumerate(expected_value["keys"]):
				self.assertEqual(si.get(field, ""), expected_value[invoice_idx][field_idx])

	def test_opening_invoice_requires_temporary_account_type(self):
		doc = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		doc.invoices[0].temporary_opening_account = "Sales - _TOIC"
		doc.save()
		doc.make_invoices()
		doc.reload()
		self.assertEqual(doc.status, "Partial Success")
		self.assertTrue(
			frappe.db.exists(
				"Opening Invoice Creation Log",
				{
					"opening_invoice_creation_tool": doc.name,
					"source_row_index": 1,
					"success": 0,
				},
			)
		)

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

		doc = self.make_invoices(
			company="_Test Opening Invoice Company",
			invoices=[{"party": party_1}, {"party": party_2}],
			return_doc=True,
		)
		doc.make_invoices()
		doc.reload()

		logs = frappe.get_all(
			"Opening Invoice Creation Log",
			filters={"opening_invoice_creation_tool": doc.name, "success": 0},
			fields=["messages", "exception"],
		)
		self.assertEqual(len(logs), 2)
		self.assertTrue(all("AccountMissingError" in log.exception for log in logs))
		self.assertEqual(doc.get_import_result_summary(), {"total": 2, "successes": 0, "failures": 2})

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

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"add_taxes_from_taxes_and_charges_template": 1, "add_taxes_from_item_tax_template": 0},
	)
	def test_opening_invoice_creation_without_taxes(self):
		company = "_Test Opening Invoice Company"
		template = frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"company": company,
				"title": "_Test Opening Invoice Tax",
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": create_account(
							account_name="_Test Opening Tax Account",
							parent_account="Duties and Taxes - _TOIC",
							account_type="Tax",
							company=company,
						),
						"description": "Test taxes",
						"rate": 9,
					}
				],
			}
		).insert()

		# makes the template the default for the party, as it would be on a live site
		make_tax_rule(tax_type="Sales", company=company, sales_tax_template=template.name, save=1)

		tool = self.make_invoices(company=company, return_doc=True)
		invoices = tool.make_invoices()
		self.assertEqual(len(invoices), 2)

		# outstanding amount is entered inclusive of tax, so taxes must not be added on top of it
		for invoice in invoices:
			si = frappe.get_doc("Sales Invoice", invoice)
			self.assertFalse(si.taxes)
			self.assertEqual(si.grand_total, 200)
			self.assertEqual(si.outstanding_amount, 200)

		# the same invoice created outside the tool keeps the default taxes,
		# since adding them there is the user's decision
		si = frappe.get_doc(tool.get_invoices()[0])
		si.flags.ignore_mandatory = True
		si.insert()
		self.assertTrue(si.taxes)
		self.assertEqual(si.grand_total, 218)

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
		doc.save()
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
				"party_type": party,
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
