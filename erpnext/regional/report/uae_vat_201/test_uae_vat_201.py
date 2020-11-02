# coding=utf-8
from __future__ import unicode_literals

import erpnext
import frappe
from unittest import TestCase
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse_account
from erpnext.regional.report.uae_vat_201.uae_vat_201 import (
	get_total_emiratewise, 
	get_tourist_tax_return_total, 
	get_tourist_tax_return_tax,
	get_zero_rated_total,
	get_exempt_total,
	get_standard_rated_expenses_total,
	get_standard_rated_expenses_tax,
)

test_dependencies = ["Territory", "Customer Group", "Supplier Group", "Item"]

class TestUaeVat201(TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company UAE VAT'")
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company UAE VAT'")


		make_company("_Test Company UAE VAT", "_TCUV")
		set_vat_accounts()

		make_customer()

		make_supplier()

		create_warehouse("_Test UAE VAT Supplier Warehouse", company="_Test Company UAE VAT")

		make_item("_Test UAE VAT Item", properties = {"is_zero_rated": 0, "is_exempt": 0})
		make_item("_Test UAE VAT Zero Rated Item", properties = {"is_zero_rated": 1, "is_exempt": 0})
		make_item("_Test UAE VAT Exempt Item", properties = {"is_zero_rated": 0, "is_exempt": 1})

		make_sales_invoices()

		create_purchase_invoices()

	def test_uae_vat_201_report(self):
		filters = {"company": "_Test Company UAE VAT"}
		total_emiratewise = get_total_emiratewise(filters)
		amounts_by_emirate = {}
		for data in total_emiratewise:
			emirate, amount, vat = data
			amounts_by_emirate[emirate] = {
				"raw_amount": amount,
				"raw_vat_amount": vat,
			}
		self.assertEqual(amounts_by_emirate["Sharjah"]["raw_amount"],300)
		self.assertEqual(amounts_by_emirate["Sharjah"]["raw_vat_amount"],5)
		self.assertEqual(amounts_by_emirate["Dubai"]["raw_amount"],200)
		self.assertEqual(amounts_by_emirate["Dubai"]["raw_vat_amount"],10)
		self.assertEqual(get_tourist_tax_return_total(filters),100)
		self.assertEqual(get_tourist_tax_return_tax(filters),2)
		self.assertEqual(get_zero_rated_total(filters),100)
		self.assertEqual(get_exempt_total(filters),100)
		self.assertEqual(get_standard_rated_expenses_total(filters),250)
		self.assertEqual(get_standard_rated_expenses_tax(filters),1)

def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": company_name,
			"abbr": abbr,
			"default_currency": "AED",
			"country": "United Arab Emirates",
			"create_chart_of_accounts_based_on": "Standard Template",
		})
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	# indempotent
	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.save()
	return company

def set_vat_accounts():
	if not frappe.db.exists("UAE VAT Settings", "_Test Company UAE VAT"):
		vat_accounts = frappe.get_all(
			"Account",
			fields=["name"],
			filters = {
				"company": "_Test Company UAE VAT",
				"is_group": 0, 
				"account_type": "Tax"
			}
		)

		uae_vat_accounts = []
		for d in vat_accounts:
			uae_vat_accounts.append(
				{
				"doctype": "UAE VAT Account", 
				"account":d.name
				})

		frappe.get_doc({
			"company": "_Test Company UAE VAT",
			"uae_vat_accounts": uae_vat_accounts,
			"doctype": "UAE VAT Settings",
		}).insert()

def make_customer():
	if not frappe.db.exists("Customer", "_Test UAE Customer"):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test UAE Customer",
			"customer_type": "Company",
		})
		customer.insert()
	else:
		customer = frappe.get_doc("Customer", "_Test UAE Customer")

def make_supplier():

	if not frappe.db.exists("Supplier", "_Test UAE Supplier"):
		frappe.get_doc({
			"supplier_group": "Local",
			"supplier_name": "_Test UAE Supplier",
			"supplier_type": "Individual",
			"doctype": "Supplier",
		}).insert()

def create_warehouse(warehouse_name, properties=None, company=None):
	if not company:
		company = "_Test Company"

	warehouse_id = erpnext.encode_company_abbr(warehouse_name, company)
	if not frappe.db.exists("Warehouse", warehouse_id):
		w = frappe.new_doc("Warehouse")
		w.warehouse_name = warehouse_name
		w.parent_warehouse = "All Warehouses - _TCUV"
		w.company = company
		w.account = get_warehouse_account(warehouse_name, company)
		if properties:
			w.update(properties)
		w.save()
		return w.name
	else:
		return warehouse_id

def make_item(item_code, properties=None):
	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_code,
		"description": item_code,
		"item_group": "Products"
	})

	if properties:
		item.update(properties)
	
	item.insert()

	return item

def make_sales_invoices():
	si = create_sales_invoice(company="_Test Company UAE VAT",
			customer = '_Test UAE Customer',
			currency = 'AED',
			warehouse = 'Finished Goods - _TCUV',
			debit_to = 'Debtors - _TCUV',
			income_account = 'Sales - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			cost_center = 'Main - _TCUV',
			sales_taxes_and_charges_template = "UAE VAT 5% - _TCUV",
			item = "_Test UAE VAT Item",
			do_not_save=1
		)
	si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 5% @ 5.0",
			"rate": 5.0
		})
	si.vat_emirate = 'Dubai'
	si.submit()

	si = create_sales_invoice(company="_Test Company UAE VAT",
			customer = '_Test UAE Customer',
			currency = 'AED',
			warehouse = 'Finished Goods - _TCUV',
			debit_to = 'Debtors - _TCUV',
			income_account = 'Sales - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			cost_center = 'Main - _TCUV',
			sales_taxes_and_charges_template = "UAE VAT 5% - _TCUV",
			item = "_Test UAE VAT Item",
			do_not_save=1
		)
	si.vat_emirate = 'Sharjah'
	si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 5% @ 5.0",
			"rate": 5.0
		})
	si.submit()

	si = create_sales_invoice(company="_Test Company UAE VAT",
			customer = '_Test UAE Customer',
			currency = 'AED',
			warehouse = 'Finished Goods - _TCUV',
			debit_to = 'Debtors - _TCUV',
			income_account = 'Sales - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			cost_center = 'Main - _TCUV',
			sales_taxes_and_charges_template = "UAE VAT 5% - _TCUV",
			item = "_Test UAE VAT Item",
			do_not_save=1
		)

	si.tourist_tax_return = 2

	si.vat_emirate = 'Dubai'

	si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 5% @ 5.0",
			"rate": 5.0
		})
	si.submit()

	si = create_sales_invoice(company="_Test Company UAE VAT",
			customer = '_Test UAE Customer',
			currency = 'AED',
			warehouse = 'Finished Goods - _TCUV',
			debit_to = 'Debtors - _TCUV',
			income_account = 'Sales - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			cost_center = 'Main - _TCUV',
			sales_taxes_and_charges_template = "UAE VAT 5% - _TCUV",
			item = "_Test UAE VAT Zero Rated Item",
			do_not_save=1
		)
	si.vat_emirate = 'Sharjah'
	si.submit()

	si = create_sales_invoice(company="_Test Company UAE VAT",
			customer = '_Test UAE Customer',
			currency = 'AED',
			warehouse = 'Finished Goods - _TCUV',
			debit_to = 'Debtors - _TCUV',
			income_account = 'Sales - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			cost_center = 'Main - _TCUV',
			sales_taxes_and_charges_template = "UAE VAT 5% - _TCUV",
			item = "_Test UAE VAT Exempt Item",
			do_not_save=1
		)
	si.vat_emirate = 'Sharjah'
	si.submit()

def create_purchase_invoices():

	pi = make_purchase_invoice(
			company="_Test Company UAE VAT",
			supplier = '_Test UAE Supplier',
			supplier_warehouse = '_Test UAE VAT Supplier Warehouse - _TCUV',
			warehouse = '_Test UAE VAT Supplier Warehouse - _TCUV',
			currency = 'AED',
			cost_center = 'Main - _TCUV',
			expense_account = 'Cost of Goods Sold - _TCUV',
			item = "_Test UAE VAT Item",
			do_not_save=1,
			uom = "Nos"
		)
	pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 5% @ 5.0",
			"rate": 5.0
		})

	pi.recoverable_standard_rated_expenses = 1

	pi.submit()
