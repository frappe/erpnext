# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import json
import unittest

import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item

test_dependencies = ["Territory", "Customer Group", "Supplier Group", "Item"]

class TestGSTR3BReport(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company GST'")
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company GST'")
		frappe.db.sql("delete from `tabGSTR 3B Report` where company='_Test Company GST'")

		make_company()
		make_item("Milk", properties = {"is_nil_exempt": 1, "standard_rate": 0.000000})
		set_account_heads()
		make_customers()
		make_suppliers()

	def test_gstr_3b_report(self):
		month_number_mapping = {
			1: "January",
			2: "February",
			3: "March",
			4: "April",
			5: "May",
			6: "June",
			7: "July",
			8: "August",
			9: "September",
			10: "October",
			11: "November",
			12: "December"
		}

		make_sales_invoice()
		create_purchase_invoices()

		if frappe.db.exists("GSTR 3B Report", "GSTR3B-March-2019-_Test Address GST-Billing"):
			report = frappe.get_doc("GSTR 3B Report", "GSTR3B-March-2019-_Test Address GST-Billing")
			report.save()
		else:
			report = frappe.get_doc({
				"doctype": "GSTR 3B Report",
				"company": "_Test Company GST",
				"company_address": "_Test Address GST-Billing",
				"year": getdate().year,
				"month": month_number_mapping.get(getdate().month)
			}).insert()

		output = json.loads(report.json_output)

		self.assertEqual(output["sup_details"]["osup_det"]["iamt"], 54)
		self.assertEqual(output["inter_sup"]["unreg_details"][0]["iamt"], 18),
		self.assertEqual(output["sup_details"]["osup_nil_exmp"]["txval"], 100),
		self.assertEqual(output["inward_sup"]["isup_details"][0]["intra"], 250)
		self.assertEqual(output["itc_elg"]["itc_avl"][4]["samt"], 22.50)
		self.assertEqual(output["itc_elg"]["itc_avl"][4]["camt"], 22.50)

	def test_gst_rounding(self):
		gst_settings = frappe.get_doc('GST Settings')
		gst_settings.round_off_gst_values = 1
		gst_settings.save()

		current_country = frappe.flags.country
		frappe.flags.country = 'India'

		si = create_sales_invoice(company="_Test Company GST",
			customer = '_Test GST Customer',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			rate=216,
			do_not_save=1
		)

		si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Output Tax IGST - _GST",
			"cost_center": "Main - _GST",
			"description": "IGST @ 18.0",
			"rate": 18
		})

		si.save()
		# Check for 39 instead of 38.88
		self.assertEqual(si.taxes[0].base_tax_amount_after_discount_amount, 39)

		frappe.flags.country = current_country
		gst_settings.round_off_gst_values = 1
		gst_settings.save()

def make_sales_invoice():
	si = create_sales_invoice(company="_Test Company GST",
			customer = '_Test GST Customer',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			do_not_save=1
		)

	si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Output Tax IGST - _GST",
			"cost_center": "Main - _GST",
			"description": "IGST @ 18.0",
			"rate": 18
		})

	si.submit()

	si1 = create_sales_invoice(company="_Test Company GST",
			customer = '_Test GST SEZ Customer',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			do_not_save=1
		)

	si1.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Output Tax IGST - _GST",
			"cost_center": "Main - _GST",
			"description": "IGST @ 18.0",
			"rate": 18
		})

	si1.submit()

	si2 = create_sales_invoice(company="_Test Company GST",
			customer = '_Test Unregistered Customer',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			do_not_save=1
		)

	si2.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Output Tax IGST - _GST",
			"cost_center": "Main - _GST",
			"description": "IGST @ 18.0",
			"rate": 18
		})

	si2.submit()

	si3 = create_sales_invoice(company="_Test Company GST",
			customer = '_Test GST Customer',
			currency = 'INR',
			item = 'Milk',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			do_not_save=1
		)
	si3.submit()

def create_purchase_invoices():
	pi = make_purchase_invoice(
			company="_Test Company GST",
			supplier = '_Test Registered Supplier',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			cost_center = 'Main - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			do_not_save=1,
		)

	pi.eligibility_for_itc = "All Other ITC"

	pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Input Tax CGST - _GST",
			"cost_center": "Main - _GST",
			"description": "CGST @ 9.0",
			"rate": 9
		})

	pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "Input Tax SGST - _GST",
			"cost_center": "Main - _GST",
			"description": "SGST @ 9.0",
			"rate": 9
		})

	pi.submit()

	pi1 = make_purchase_invoice(
			company="_Test Company GST",
			supplier = '_Test Registered Supplier',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			cost_center = 'Main - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			item = "Milk",
			do_not_save=1
		)

	pi1.shipping_address = "_Test Supplier GST-1-Billing"
	pi1.save()

	pi1.submit()

	pi2 = make_purchase_invoice(company="_Test Company GST",
			customer = '_Test Registered Supplier',
			currency = 'INR',
			item = 'Milk',
			warehouse = 'Finished Goods - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			rate=250,
			qty=1,
			do_not_save=1
		)
	pi2.submit()

def make_suppliers():
	if not frappe.db.exists("Supplier", "_Test Registered Supplier"):
		frappe.get_doc({
			"supplier_group": "_Test Supplier Group",
			"supplier_name": "_Test Registered Supplier",
			"gst_category": "Registered Regular",
			"supplier_type": "Individual",
			"doctype": "Supplier",
		}).insert()

	if not frappe.db.exists("Supplier", "_Test Unregistered Supplier"):
		frappe.get_doc({
			"supplier_group": "_Test Supplier Group",
			"supplier_name": "_Test Unregistered Supplier",
			"gst_category": "Unregistered",
			"supplier_type": "Individual",
			"doctype": "Supplier",
		}).insert()

	if not frappe.db.exists('Address', '_Test Supplier GST-1-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test Supplier GST-1",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gstin": "29AACCV0498C1Z9",
			"gst_state": "Karnataka",
		}).insert()

		address.append("links", {
			"link_doctype": "Supplier",
			"link_name": "_Test Registered Supplier"
		})

		address.is_shipping_address = 1
		address.save()

	if not frappe.db.exists('Address', '_Test Supplier GST-2-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test Supplier GST-2",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gst_state": "Karnataka",
		}).insert()

		address.append("links", {
			"link_doctype": "Supplier",
			"link_name": "_Test Unregistered Supplier"
		})

		address.save()

def make_customers():
	if not frappe.db.exists("Customer", "_Test GST Customer"):
		frappe.get_doc({
			"customer_group": "_Test Customer Group",
			"customer_name": "_Test GST Customer",
			"gst_category": "Registered Regular",
			"customer_type": "Individual",
			"doctype": "Customer",
			"territory": "_Test Territory"
		}).insert()

	if not frappe.db.exists("Customer", "_Test GST SEZ Customer"):
		frappe.get_doc({
			"customer_group": "_Test Customer Group",
			"customer_name": "_Test GST SEZ Customer",
			"gst_category": "SEZ",
			"customer_type": "Individual",
			"doctype": "Customer",
			"territory": "_Test Territory"
		}).insert()

	if not frappe.db.exists("Customer", "_Test Unregistered Customer"):
		frappe.get_doc({
			"customer_group": "_Test Customer Group",
			"customer_name": "_Test Unregistered Customer",
			"gst_category": "Unregistered",
			"customer_type": "Individual",
			"doctype": "Customer",
			"territory": "_Test Territory"
		}).insert()

	if not frappe.db.exists('Address', '_Test GST-1-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test GST-1",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gstin": "29AZWPS7135H1ZG",
			"gst_state": "Karnataka",
			"gst_state_number": "29"
		}).insert()

		address.append("links", {
			"link_doctype": "Customer",
			"link_name": "_Test GST Customer"
		})

		address.save()

	if not frappe.db.exists('Address', '_Test GST-2-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test GST-2",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gst_state": "Haryana",
		}).insert()

		address.append("links", {
			"link_doctype": "Customer",
			"link_name": "_Test Unregistered Customer"
		})

		address.save()

	if not frappe.db.exists('Address', '_Test GST-3-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test GST-3",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gst_state": "Gujarat",
		}).insert()

		address.append("links", {
			"link_doctype": "Customer",
			"link_name": "_Test GST SEZ Customer"
		})

		address.save()

def make_company():
	if frappe.db.exists("Company", "_Test Company GST"):
		return

	company = frappe.new_doc("Company")
	company.company_name = "_Test Company GST"
	company.abbr = "_GST"
	company.default_currency = "INR"
	company.country = "India"
	company.insert()

	if not frappe.db.exists('Address', '_Test Address GST-Billing'):
		address = frappe.get_doc({
			"address_title": "_Test Address GST",
			"address_line1": "_Test Address Line 1",
			"address_type": "Billing",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"doctype": "Address",
			"is_primary_address": 1,
			"phone": "+91 0000000000",
			"gstin": "27AAECE4835E1ZR",
			"gst_state": "Maharashtra",
			"gst_state_number": "27"
		}).insert()

		address.append("links", {
			"link_doctype": "Company",
			"link_name": "_Test Company GST"
		})

		address.save()

def set_account_heads():
	gst_settings = frappe.get_doc("GST Settings")

	gst_account = frappe.get_all(
		"GST Account",
		fields=["cgst_account", "sgst_account", "igst_account"],
		filters = {"company": "_Test Company GST"})

	if not gst_account:
		gst_settings.append("gst_accounts", {
			"company": "_Test Company GST",
			"cgst_account": "Output Tax CGST - _GST",
			"sgst_account": "Output Tax SGST - _GST",
			"igst_account": "Output Tax IGST - _GST"
		})

		gst_settings.save()
