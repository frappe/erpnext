# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
	get_temporary_opening_account,
	start_import,
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
		invoices = doc.make_invoices()
		sales_invoice_1 = frappe.get_doc("Sales Invoice", invoices[0])
		sales_invoice_2 = frappe.get_doc("Sales Invoice", invoices[1])

		self.assertEqual(sales_invoice_1.items[0].project, project_1.name)
		self.assertEqual(sales_invoice_2.items[0].project, project_2.name)

	def test_party_currency_does_not_change_company_currency_amount(self):
		for invoice_type, party_type in (("Sales", "Customer"), ("Purchase", "Supplier")):
			with self.subTest(invoice_type=invoice_type):
				frappe.db.set_value(party_type, f"_Test {party_type}", "default_currency", "USD")
				tool = self.make_invoices(
					invoice_type=invoice_type, company="_Test Opening Invoice Company", return_doc=True
				)
				tool.invoices = tool.invoices[:1]
				tool.invoices[0].outstanding_amount = 1000
				names = tool.make_invoices()
				self.assertEqual(len(names), 1)
				invoice = frappe.get_doc(f"{invoice_type} Invoice", names[0])
				self.assertEqual(invoice.currency, "INR")
				self.assertEqual(invoice.base_grand_total, 1000)
				self.assertEqual(invoice.outstanding_amount, 1000)

	def test_explicit_foreign_currency_and_summary(self):
		company = "_Test Opening Invoice Company"
		tool = self.make_invoices(company=company, return_doc=True)
		before = tool.get_opening_invoice_summary()[0]
		for invoice_type, party_type, account_type, parent_account in (
			("Sales", "Customer", "Receivable", "Accounts Receivable - _TOIC"),
			("Purchase", "Supplier", "Payable", "Accounts Payable - _TOIC"),
		):
			with self.subTest(invoice_type=invoice_type):
				account = create_account(
					account_name=f"_Test Opening {account_type} USD",
					parent_account=parent_account,
					company=company,
					account_type=account_type,
					account_currency="USD",
				)
				party = frappe.copy_doc(frappe.get_doc(party_type, f"_Test {party_type}"))
				party.set(party_type.lower() + "_name", f"_Test Opening USD {party_type}")
				party.default_currency = "USD"
				party.set("accounts", [])
				party.append("accounts", {"company": company, "account": account})
				party.insert()
				tool = self.make_invoices(invoice_type=invoice_type, company=company, return_doc=True)
				tool.invoices = tool.invoices[:1]
				tool.invoices[0].party = party.name
				tool.invoices[0].currency = "USD"
				tool.invoices[0].outstanding_amount = 1000
				invoices = tool.get_invoices()
				invoices[0].conversion_rate = 83
				names = start_import(invoices)
				self.assertEqual(len(names), 1)
				invoice = frappe.get_doc(f"{invoice_type} Invoice", names[0])
				self.assertEqual(invoice.currency, "USD")
				self.assertEqual(invoice.outstanding_amount, 1000)
				self.assertEqual(invoice.base_grand_total, 83000)
				entries = frappe.get_all(
					"GL Entry",
					filters={"voucher_type": invoice.doctype, "voucher_no": invoice.name, "account": account},
					fields=["debit", "credit"],
				)
				self.assertEqual(len(entries), 1)
				self.assertEqual(entries[0].debit or entries[0].credit, 83000)
				summary = tool.get_opening_invoice_summary()[0]
				previous = before.get(company, {}).get(invoice.doctype, {}).get("outstanding_amount", 0)
				self.assertEqual(summary[company][invoice.doctype].outstanding_amount - previous, 83000)

	def test_summary_does_not_convert_company_currency_receivable_twice(self):
		company = "_Test Opening Invoice Company"
		tool = self.make_invoices(company=company, return_doc=True)
		before = tool.get_opening_invoice_summary()[0]
		tool.invoices = tool.invoices[:1]
		tool.invoices[0].currency = "USD"
		tool.invoices[0].outstanding_amount = 1000
		invoices = tool.get_invoices()
		invoices[0].conversion_rate = 83
		names = start_import(invoices)
		self.assertEqual(len(names), 1)
		invoice = frappe.get_doc("Sales Invoice", names[0])
		self.assertEqual(invoice.party_account_currency, "INR")
		self.assertEqual(invoice.outstanding_amount, 83000)
		summary = tool.get_opening_invoice_summary()[0]
		previous = before.get(company, {}).get(invoice.doctype, {}).get("outstanding_amount", 0)
		self.assertEqual(summary[company][invoice.doctype].outstanding_amount - previous, 83000)

	def test_existing_party_name_is_reused(self):
		for invoice_type, party_type in (("Sales", "Customer"), ("Purchase", "Supplier")):
			with self.subTest(invoice_type=invoice_type):
				tool = self.make_invoices(
					invoice_type=invoice_type, company="_Test Opening Invoice Company", return_doc=True
				)
				tool.create_missing_party = 1
				party = f"_Test {party_type}"
				party_name = frappe.db.get_value(party_type, party, party_type.lower() + "_name")
				for row in tool.invoices:
					row.party = None
					row.party_name = party_name
				count = frappe.db.count(party_type)
				names = tool.make_invoices()
				self.assertEqual(len(names), 2)
				self.assertEqual(frappe.db.count(party_type), count)
				for name in names:
					self.assertEqual(
						frappe.db.get_value(f"{invoice_type} Invoice", name, party_type.lower()), party
					)

	def test_ambiguous_party_name_requires_party_id(self):
		tool = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		customer = frappe.copy_doc(frappe.get_doc("Customer", "_Test Customer"))
		customer.insert()
		tool.create_missing_party = 1
		tool.invoices[0].party = None
		tool.invoices[0].party_name = customer.customer_name
		with self.assertRaisesRegex(frappe.ValidationError, "Please select the Party ID"):
			tool.make_invoices()

	def test_missing_party_creation_requires_permission(self):
		tool = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
		with self.set_user("Guest"):
			self.assertRaises(
				frappe.PermissionError, tool.add_party, "Customer", "_Test Missing Opening Customer"
			)

	def test_quantity_rounding_preserves_opening_amount(self):
		for invoice_type in ("Sales", "Purchase"):
			for qty, amount in ((3, 100), (7, 1000), (2, 100), (1.234, 1000)):
				with self.subTest(invoice_type=invoice_type, qty=qty):
					tool = self.make_invoices(
						invoice_type=invoice_type, company="_Test Opening Invoice Company", return_doc=True
					)
					tool.invoices = tool.invoices[:1]
					tool.invoices[0].qty = str(qty)
					tool.invoices[0].outstanding_amount = amount
					names = tool.make_invoices()
					self.assertEqual(len(names), 1)
					invoice = frappe.get_doc(f"{invoice_type} Invoice", names[0])
					self.assertEqual(invoice.grand_total, amount)
					self.assertEqual(invoice.outstanding_amount, amount)
					if invoice.items[0].qty != qty:
						self.assertIn(f"Original Quantity: {qty}", invoice.items[0].description)

	def test_invalid_quantity_is_rejected_before_import(self):
		for qty in ("0", "two", "-1", "nan", "inf"):
			with self.subTest(qty=qty):
				tool = self.make_invoices(company="_Test Opening Invoice Company", return_doc=True)
				tool.invoices[1].qty = qty
				with self.assertRaisesRegex(
					frappe.ValidationError, "Row #2: Quantity must be a positive number"
				):
					tool.make_invoices()

	def test_opening_invoice_skips_credit_and_overdue_checks(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

		with (
			patch.object(SalesInvoice, "check_credit_limit") as credit_check,
			patch.object(SalesInvoice, "check_overdue_billing_threshold") as overdue_check,
		):
			names = self.make_invoices(company="_Test Opening Invoice Company")
			self.assertEqual(len(names), 2)
			credit_check.assert_not_called()
			overdue_check.assert_not_called()

		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		with (
			patch.object(SalesInvoice, "check_credit_limit") as credit_check,
			patch.object(SalesInvoice, "check_overdue_billing_threshold") as overdue_check,
		):
			create_sales_invoice(uom=frappe.get_cached_value("Item", "_Test Item", "stock_uom"))
			credit_check.assert_called_once()
			overdue_check.assert_called_once()

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{
			"credit_controller": "",
			"enable_overdue_billing_threshold": 1,
			"role_allowed_to_bypass_overdue_billing": "",
		},
	)
	def test_existing_balances_can_exceed_credit_and_overdue_limits(self):
		from erpnext.selling.doctype.customer.customer import (
			check_credit_limit,
			check_overdue_billing_threshold,
		)

		company = "_Test Opening Invoice Company"
		customer = frappe.get_doc("Customer", make_customer("_Test Opening Credit Customer"))
		customer.append(
			"credit_limits", {"company": company, "credit_limit": 5000, "overdue_billing_threshold": 5000}
		)
		customer.save()
		names = self.make_invoices(
			company=company,
			invoices=[
				{"party": customer.name, "outstanding_amount": 3000},
				{"party": customer.name, "outstanding_amount": 4000},
			],
		)
		self.assertEqual(len(names), 2)
		self.assertEqual(
			sum(frappe.db.get_value("Sales Invoice", name, "outstanding_amount") for name in names), 7000
		)
		self.assertRaises(frappe.ValidationError, check_credit_limit, customer.name, company)
		self.assertRaises(frappe.ValidationError, check_overdue_billing_threshold, customer.name, company)


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
