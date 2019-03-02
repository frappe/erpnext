# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
import json

class TestGSTR3BReport(unittest.TestCase):
	def test_gstr_3b_report(self):
		frappe.set_user("Administrator")

		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company GST'")
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company GST'")

		make_company()
		set_account_heads()
		make_customer()
		make_sales_invoice()

		if frappe.db.exists("GSTR 3B Report", "GSTR3B-March-2019"):
			report = frappe.get_doc("GSTR 3B Report", "GSTR3B-March-2019")
		else:
			report = frappe.get_doc({
				"doctype": "GSTR 3B Report",
				"company": "_Test Company GST",
				"year": "2019",
				"month": "March"
			}).insert()

		output = json.loads(report.json_output)
		self.assertEqual(output["sup_details"]["osup_det"]["iamt"], 18),

def make_sales_invoice():
	si = create_sales_invoice(company="_Test Company GST",
			customer = '_Test GST Customer',
			currency = 'INR',
			warehouse = 'Finished Goods - _GST',
			debit_to = 'Debtors - _GST',
			income_account = 'Sales - _GST',
			expense_account = 'Cost of Goods Sold - _GST',
			cost_center = 'Main - _GST',
			posting_date = '2019-03-10',
			do_not_save=1
		)

	si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "IGST - _GST",
			"cost_center": "Main - _GST",
			"description": "IGST @ 18.0",
			"rate": 18
		})

	si.submit()

def make_customer():

	if frappe.db.exists("Customer", "_Test GST Customer"):
		return

	frappe.get_doc({
		 "customer_group": "_Test Customer Group",
		 "customer_name": "_Test GST Customer",
		 "gst_category": "Registered Regular",
		 "customer_type": "Individual",
		 "doctype": "Customer",
		 "territory": "_Test Territory"
	}).insert(ignore_permissions=True)

def make_company():

	if not frappe.db.exists('Address', '_Test Address-Billing'):
		address = frappe.get_doc({
			"address_line1": "_Test Address Line 1",
			"address_title": "_Test Address",
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

	if frappe.db.exists("Company", "_Test Company GST"):
		return
	company = frappe.new_doc("Company")
	company.company_name = "_Test Company GST"
	company.abbr = "_GST"
	company.default_currency = "INR"
	company.country = "India"
	company.insert()

def set_account_heads():

	gst_settings = frappe.get_doc("GST Settings")

	gst_account = frappe.get_all(
		"GST Account",
		fields=["cgst_account", "sgst_account", "igst_account"],
		filters = {"company": "_Test Company GST"})

	if not gst_account:
		gst_settings.append("gst_accounts", {
			"company": "_Test Company GST",
			"cgst_account": "CGST - _GST",
			"sgst_account": "SGST - _GST",
			"igst_account": "IGST - _GST",
		})

		gst_settings.save()


