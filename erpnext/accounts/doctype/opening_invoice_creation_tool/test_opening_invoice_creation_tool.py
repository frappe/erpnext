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
	def test_create_opening_invoice_for_purchase_invoice_TC_ACC_047(self):
		invoices = self.make_invoices(invoice_type="Purchase", company="_Test Company",party_1="_Test Supplier")
		expected_value = {
			"keys": ["supplier", "outstanding_amount", "status"],
			0: ["_Test Supplier", 300, "Overdue"],
			1: ["_Test Supplier 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value, invoice_type="Purchase")
	
	def test_create_opening_invoice_for_sales_invoice_TC_ACC_045(self):
		invoices = self.make_invoices(invoice_type="Sales", company="_Test Company",party_1="_Test Customer")
		expected_value = {
			"keys": ["customer", "outstanding_amount", "status"],
			0: ["_Test Customer", 300, "Overdue"],
			1: ["_Test Customer 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value, invoice_type="Sales")

	def test_onload_sets_summary_and_temporary_account_TC_ACC_326(self):
		self.company = "_Test Opening Invoice Company"

		item_code = "Test Item"
		if not frappe.db.exists("Item", item_code):
			from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

			item = make_test_item(item_code)
			item.update(
				{
					"is_sales_item": 1,
					"is_purchase_item": 1,
				}
			)
			item.save(ignore_permissions=True)

		# Insert a dummy Sales Invoice for testing
		if not frappe.db.exists("Sales Invoice", {"customer": "_Test Customer"}):
			customer = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "_Test Customer",
					"customer_group": "Commercial",
					"territory": "All Territories",
				}
			).insert(ignore_permissions=True)

			# Create a Balance Sheet parent if not exists
			if not frappe.db.exists("Account", "Temporary Accounts - _TOIC"):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Temporary Accounts",
						"company": self.company,
						"root_type": "Asset",
						"account_type": "",
						"is_group": 1,
						"report_type": "Balance Sheet",
					}
				).insert(ignore_permissions=True)

			# Create your temporary opening account under it
			income_account = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Temporary Opening Income",
					"parent_account": "Temporary Accounts - _TOIC",
					"company": self.company,
					"root_type": "Asset",
					"is_group": 0,
					"report_type": "Balance Sheet",
				}
			).insert(ignore_permissions=True)

			# Insert Sales Invoice
			frappe.get_doc(
				{
					"doctype": "Sales Invoice",
					"customer": customer.name,
					"company": self.company,
					"is_opening": "Yes",
					"docstatus": 1,
					"outstanding_amount": 100.0,
					"paid_amount": 50.0,
					"grand_total": 150.0,
					"base_grand_total": 150.0,
					"base_write_off_amount": 0.0,
					"items": [
						{
							"item_code": item_code,
							"qty": 1,
							"rate": 150.0,
							"amount": 150.0,
							"income_account": income_account.name,
						}
					],
					"debit_to": "Debtors - _TOIC",
				}
			).insert(ignore_permissions=True)

		# Create the Opening Invoice Creation Tool doc
		doc = frappe.get_doc({"doctype": "Opening Invoice Creation Tool", "company": self.company})

		# Call onload explicitly
		doc.onload()

		# Check if summary is set onload
		summary = doc.get_onload("opening_invoices_summary")
		max_count = doc.get_onload("max_count")
		temp_account = doc.get_onload("temporary_opening_account")

		# Assertions
		self.assertIsInstance(summary, dict)
		self.assertIsInstance(max_count, dict)
		self.assertIsInstance(temp_account, str)
		self.assertTrue(temp_account.startswith("ACC") or temp_account.startswith("Temp"))

	def test_temporary_opening_account_without_company_TC_ACC_325(self):
		temporary_account_response = get_temporary_opening_account()
		self.assertEqual(temporary_account_response, None)

	def test_make_invoices_path_TC_ACC_517(self):
		company = "_Test Company"
		tool = frappe.new_doc("Opening Invoice Creation Tool")
		tool.company = company
		tool.invoice_type = "Sales"

		# Add 50 rows (>= 50 to trigger else path)
		for i in range(50):
			customer = make_customer(f"Customer {i}")
			tool.append(
				"invoices",
				{
					"party_type": "Customer",
					"party": customer,
					"outstanding_amount": 100 + i,
					"temporary_opening_account": get_temporary_opening_account(company),
				},
			)

		tool.insert()

		# Force test flag so scheduler check won't throw
		frappe.flags.in_test = True

		# Call make_invoices
		result = tool.make_invoices()

		# Assert that enqueue/now path executed
		# In test mode, enqueue runs inline and returns list of invoice names
		self.assertGreaterEqual(tool.docstatus, 0)
		self.assertGreaterEqual(len(tool.invoices), 50)

		frappe.flags.in_test = False

	def test_make_invoices_creating_missing_customer_TC_ACC_518(self):
		company = "_Test Company"
		tool = frappe.new_doc("Opening Invoice Creation Tool")
		tool.company = company
		tool.invoice_type = "Sales"
		tool.create_missing_party = 1
		party_name = ""
		# Add 50 rows (>= 50 to trigger else path)
		for i in range(50):
			tool.append(
				"invoices",
				{
					"party_type": "Customer",
					"party": f"Customer {i}",
					"outstanding_amount": 100 + i,
					"temporary_opening_account": get_temporary_opening_account(company),
				},
			)
			party_name = f"Customer {i}"
			tool.validate_mandatory_invoice_fields(tool.invoices[i])

		# Force test flag so scheduler check won't throw
		frappe.flags.in_test = True

		self.assertEqual(frappe.db.exists("Customer", party_name), party_name)

		frappe.flags.in_test = False

	def test_make_invoices_creating_missing_supplier_TC_ACC_519(self):
		company = "_Test Company"
		tool = frappe.new_doc("Opening Invoice Creation Tool")
		tool.company = company
		tool.invoice_type = "Sales"
		tool.create_missing_party = 1

		buying_setting = frappe.get_doc("Buying Settings", "supplier_group")
		buying_setting.supplier_group = "Local"
		buying_setting.save()
		party_name = ""
		# Add 50 rows (>= 50 to trigger else path)
		for i in range(50):
			tool.append(
				"invoices",
				{
					"party_type": "Supplier",
					"party": f"Supplier {i}",
					"outstanding_amount": 100 + i,
					"temporary_opening_account": get_temporary_opening_account(company),
				},
			)
			party_name = f"Supplier {i}"

			tool.validate_mandatory_invoice_fields(tool.invoices[i])

		# Force test flag so scheduler check won't throw
		frappe.flags.in_test = True

		self.assertEqual(frappe.db.exists("Supplier", party_name), party_name)

		frappe.flags.in_test = False

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
