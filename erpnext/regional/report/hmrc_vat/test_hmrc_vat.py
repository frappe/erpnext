# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.regional.report.hmrc_vat.hmrc_vat import UKVatReport, execute

# from erpnext.stock.doctype.item.test_item import create_item

EXTRA_TEST_RECORD_DEPENDENCIES = [
	"Account",
	"Company",
	"Customer",
	"Customer Group",
	"Warehouse",
	"Item",
	"Item Group",
	"Supplier Group",
	"User",
]
# IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class TestHMRCVAT(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# frappe.set_user("Administrator")
		make_company("_Test Company UK VAT", "_TCUV")

		create_account(
			account_name="Input VAT",
			account_type="Tax",
			parent_account="Tax Assets - _TCUV",
			company="_Test Company UK VAT",
		)
		create_account(
			account_name="VAT",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCUV",
			company="_Test Company UK VAT",
		)

		ensure_item_groups()
		ensure_party_groups()

		make_item("_Test UK VAT Item")
		make_item("_Test UK VAT Zero Rated Item")

		make_customer()
		make_supplier()

		make_sales_invoices()
		create_purchase_invoices()

	def tearDown(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company UK VAT'")
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company UK VAT'")
		frappe.delete_doc("Company", "_Test Company UK VAT")
		super().tearDown()

	def test_get_accounts(self):
		filters = {"company": "_Test Company UK VAT", "from_date": today(), "to_date": today()}
		vat_report = UKVatReport(filters)
		vat_accounts = vat_report.get_vat_accounts()
		self.assertIn("VAT - _TCUV", vat_accounts)
		self.assertIn("Input VAT - _TCUV", vat_accounts)

	def test_hmrc_vat(self):
		filters = {"company": "_Test Company UK VAT", "from_date": today(), "to_date": today()}
		columns, data = execute(filters)
		total_tax_amount = 0
		total_row_tax = 0
		for row in data:
			keys = row.keys()
			# skips total row tax_amount in if.. and skips section header in elif..
			if "voucher_no" in keys:
				total_tax_amount = total_tax_amount + row["tax_amount"]
			elif "tax_amount" in keys:
				total_row_tax = total_row_tax + row["tax_amount"]

		self.assertEqual(len(data), 2)
		self.assertEqual(total_tax_amount, total_row_tax)


def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"default_currency": "GBP",
				"country": "United Kingdom",
				"create_chart_of_accounts_based_on": "Standard Template",
			}
		)
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	if not frappe.db.exists("Warehouse Type", "Transit"):
		warehouse_type = frappe.get_doc(
			{"doctype": "Warehouse Type", "warehouse_type": "Transit", "name": "Transit"}
		)
		warehouse_type.insert()

	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.save()

	return company


def make_customer():
	if not frappe.db.exists("Customer", "_Test UK Customer"):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test UK Customer",
				"customer_type": "Company",
				"customer_group": "All Customer Groups",
			}
		).insert()


def make_supplier():
	if not frappe.db.exists("Supplier", "_Test UK Supplier"):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test UK Supplier",
				"supplier_type": "Company",
				"supplier_group": "All Supplier Groups",
			}
		).insert()


def ensure_item_groups():
	if not frappe.db.exists("Item Group", "All Item Groups"):
		make_item_group("All Item Groups", is_group=1, parent_item_group=None)

	if not frappe.db.exists("Item Group", "Products"):
		make_item_group("Products", is_group=0)


def ensure_party_groups():
	if not frappe.db.exists("Customer Group", "All Customer Groups"):
		make_customer_group("All Customer Groups", is_group=1, parent_customer_group=None)

	if not frappe.db.exists("Supplier Group", "All Supplier Groups"):
		make_supplier_group("All Supplier Groups", is_group=1, parent_supplier_group=None)


def make_item_group(item_group_name, is_group=0, parent_item_group="All Item Groups", properties=None):
	if not frappe.db.exists("Item Group", item_group_name):
		item_group_dict = {
			"doctype": "Item Group",
			"item_group_name": item_group_name,
			"is_group": is_group,
		}

		if parent_item_group is not None:
			item_group_dict["parent_item_group"] = parent_item_group

		item_group = frappe.get_doc(item_group_dict)
		if properties:
			item_group.update(properties)
		item_group.insert()


def make_customer_group(
	customer_group_name, is_group=0, parent_customer_group="All Customer Groups", properties=None
):
	if not frappe.db.exists("Customer Group", customer_group_name):
		customer_group_dict = {
			"doctype": "Customer Group",
			"customer_group_name": customer_group_name,
			"is_group": is_group,
		}

		if parent_customer_group is not None:
			customer_group_dict["parent_customer_group"] = parent_customer_group

		customer_group = frappe.get_doc(customer_group_dict)
		if properties:
			customer_group.update(properties)
		customer_group.insert()


def make_supplier_group(
	supplier_group_name, is_group=0, parent_supplier_group="All Supplier Groups", properties=None
):
	if not frappe.db.exists("Supplier Group", supplier_group_name):
		supplier_group_dict = {
			"doctype": "Supplier Group",
			"supplier_group_name": supplier_group_name,
			"is_group": is_group,
		}

		if parent_supplier_group is not None:
			supplier_group_dict["parent_supplier_group"] = parent_supplier_group

		supplier_group = frappe.get_doc(supplier_group_dict)
		if properties:
			supplier_group.update(properties)
		supplier_group.insert()


def make_item(item_code, properties=None):
	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"description": item_code,
				"item_group": "Products",
			}
		)

		if properties:
			item.update(properties)

		item.insert()


def make_sales_invoices():
	def make_sales_invoices_wrapper(item, rate, tax_account, tax_rate, tax=True):
		si = create_sales_invoice(
			company="_Test Company UK VAT",
			customer="_Test UK Customer",
			currency="GBP",
			item=item,
			rate=rate,
			warehouse="Finished Goods - _TCUV",
			debit_to="Debtors - _TCUV",
			income_account="Sales - _TCUV",
			expense_account="Cost of Goods Sold - _TCUV",
			cost_center="Main - _TCUV",
			do_not_save=1,
		)
		if tax:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax_account,
					"cost_center": "Main - _TCUV",
					"description": "VAT 20% @ 20.0",
					"rate": tax_rate,
				},
			)

		si.submit()

	test_item = "_Test UK VAT Item"
	test_zero_rated_item = "_Test UK VAT Zero Rated Item"

	print("Making Two Sales Invoices...")
	make_sales_invoices_wrapper(test_item, 100.0, "VAT - _TCUV", 20.0)
	make_sales_invoices_wrapper(test_zero_rated_item, 100.0, "VAT - _TCUV", 0.0)


def create_purchase_invoices():
	pi = make_purchase_invoice(
		company="_Test Company UK VAT",
		supplier="_Test UK Supplier",
		supplier_warehouse="Finished Goods - _TCUV",
		warehouse="Finished Goods - _TCUV",
		currency="GBP",
		cost_center="Main - _TCUV",
		expense_account="Cost of Goods Sold - _TCUV",
		item="_Test UK VAT Item",
		qty=1,
		rate=100,
		uom="Nos",
		do_not_save=1,
	)
	pi.append(
		"taxes",
		{
			"charge_type": "On Net Total",
			"account_head": "Input VAT - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 20% @ 20.0",
			"rate": 20.0,
		},
	)

	print("Submitting One Purchase Invoice...")
	pi.submit()
