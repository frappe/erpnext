# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from unittest import TestCase

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.regional.report.vat_audit_report.vat_audit_report import execute


class TestVATAuditReport(TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		make_company("_Test Company SA VAT", "_TCSV")

		create_account(
			account_name="VAT - 0%",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCSV",
			company="_Test Company SA VAT",
		)
		create_account(
			account_name="VAT - 15%",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCSV",
			company="_Test Company SA VAT",
		)
		set_sa_vat_accounts()

		make_item("_Test SA VAT Item")
		make_item("_Test SA VAT Zero Rated Item", properties={"is_zero_rated": 1})

		make_customer()
		make_supplier()

		make_sales_invoices()
		create_purchase_invoices()

	def tearDown(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company SA VAT'")
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company SA VAT'")

	def test_vat_audit_report(self):
		filters = {"company": "_Test Company SA VAT", "from_date": today(), "to_date": today()}
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

		self.assertEqual(total_tax_amount, total_row_tax)


def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"default_currency": "ZAR",
				"country": "South Africa",
				"create_chart_of_accounts_based_on": "Standard Template",
			}
		)
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.save()

	return company


def set_sa_vat_accounts():
	if not frappe.db.exists("South Africa VAT Settings", "_Test Company SA VAT"):
		vat_accounts = frappe.get_all(
			"Account",
			fields=["name"],
			filters={"company": "_Test Company SA VAT", "is_group": 0, "account_type": "Tax"},
		)

		sa_vat_accounts = []
		for account in vat_accounts:
			sa_vat_accounts.append({"doctype": "South Africa VAT Account", "account": account.name})

		frappe.get_doc(
			{
				"company": "_Test Company SA VAT",
				"vat_accounts": sa_vat_accounts,
				"doctype": "South Africa VAT Settings",
			}
		).insert()


def make_customer():
	if not frappe.db.exists("Customer", "_Test SA Customer"):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test SA Customer",
				"customer_type": "Company",
			}
		).insert()


def make_supplier():
	if not frappe.db.exists("Supplier", "_Test SA Supplier"):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test SA Supplier",
				"supplier_type": "Company",
				"supplier_group": "All Supplier Groups",
			}
		).insert()


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
			company="_Test Company SA VAT",
			customer="_Test SA Customer",
			currency="ZAR",
			item=item,
			rate=rate,
			warehouse="Finished Goods - _TCSV",
			debit_to="Debtors - _TCSV",
			income_account="Sales - _TCSV",
			expense_account="Cost of Goods Sold - _TCSV",
			cost_center="Main - _TCSV",
			do_not_save=1,
		)
		if tax:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax_account,
					"cost_center": "Main - _TCSV",
					"description": "VAT 15% @ 15.0",
					"rate": tax_rate,
				},
			)

		si.submit()

	test_item = "_Test SA VAT Item"
	test_zero_rated_item = "_Test SA VAT Zero Rated Item"

	make_sales_invoices_wrapper(test_item, 100.0, "VAT - 15% - _TCSV", 15.0)
	make_sales_invoices_wrapper(test_zero_rated_item, 100.0, "VAT - 0% - _TCSV", 0.0)


def create_purchase_invoices():
	pi = make_purchase_invoice(
		company="_Test Company SA VAT",
		supplier="_Test SA Supplier",
		supplier_warehouse="Finished Goods - _TCSV",
		warehouse="Finished Goods - _TCSV",
		currency="ZAR",
		cost_center="Main - _TCSV",
		expense_account="Cost of Goods Sold - _TCSV",
		item="_Test SA VAT Item",
		qty=1,
		rate=100,
		uom="Nos",
		do_not_save=1,
	)
	pi.append(
		"taxes",
		{
			"charge_type": "On Net Total",
			"account_head": "VAT - 15% - _TCSV",
			"cost_center": "Main - _TCSV",
			"description": "VAT 15% @ 15.0",
			"rate": 15.0,
		},
	)

	pi.submit()
