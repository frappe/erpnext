# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.model
from webnotes.model.doclist import DocList
from webnotes.utils import nowdate

from stock.doctype.purchase_receipt import test_purchase_receipt

company = webnotes.conn.get_default("company")
abbr = webnotes.conn.get_value("Company", company, "abbr")

def load_data():
	test_purchase_receipt.load_data()
	
	# create customer group
	webnotes.insert({"doctype": "Customer Group",
		"customer_group_name": "Default Customer Group",
		"parent_customer_group": "All Customer Groups", "is_group": "No"})
	
	# create customer
	webnotes.insert({"doctype": "Customer", "customer_name": "West Wind Inc.",
		"customer_type": "Company", "territory": "Default",
		"customer_group": "Default Customer Group", "company": company,
		"credit_days": 50, "credit_limit": 0})
	
	webnotes.insert({"doctype": "Account", "account_name": "Sales",
		"parent_account": "Income - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "Excise Duty",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "Education Cess",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "S&H Education Cess",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	webnotes.insert({"doctype": "Account", "account_name": "CST",
		"parent_account": "Direct Expenses - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	webnotes.insert({"doctype": "Account", "account_name": "adj_rate",
		"parent_account": "Direct Expenses - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	from webnotes.model.doc import Document
	item = Document("Item", "Home Desktop 100")
	
	# excise duty
	item_tax = item.addchild("item_tax", "Item Tax")
	item_tax.tax_type = "Excise Duty - %s" % abbr
	item_tax.tax_rate = 10
	item_tax.save()

import json	
sales_invoice_doclist = [
	# parent
	{
		"doctype": "Sales Invoice", 
		"debit_to": "West Wind Inc. - %s" % abbr,
		"customer_name": "West Wind Inc.",
		"naming_series": "INV", "posting_date": nowdate(),
		"company": company, "fiscal_year": webnotes.conn.get_default("fiscal_year"), 
		"currency": webnotes.conn.get_default("currency"), "conversion_rate": 1.0,
		"price_list_currency": webnotes.conn.get_default("currency"),
		"plc_conversion_rate": 1.0, "net_total": 1250, "grand_total": 1627.05, 
		"grand_total_export": 1627.05
	},
	# items
	{
		"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		"item_code": "Home Desktop 100", "qty": 10, "basic_rate": 50, "amount": 500, 
		"parentfield": "entries", "so_detail": None, "dn_detail": None,
		"uom": "Nos", "item_tax_rate": json.dumps({"Excise Duty - %s" % abbr: 10}),
		"income_account": "Sales - %s" % abbr, 
		"cost_center": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		"item_code": "Home Desktop 200", "qty": 5, "basic_rate": 150, "amount": 750,
		"so_detail": None, "dn_detail": None, 
		"parentfield": "entries", "uom": "Nos", "income_account": "Sales - %s" % abbr, 
		"cost_center": "Default Cost Center - %s" % abbr
	},
	# taxes
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "Actual",
		"account_head": "Shipping Charges - %s" % abbr, "rate": 100, "tax_amount": 100,
		"parentfield": "other_charges",
		"cost_center_other_charges": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "Customs Duty - %s" % abbr, "rate": 10, "tax_amount": 125,
		"parentfield": "other_charges",
		"cost_center_other_charges": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "Excise Duty - %s" % abbr, "rate": 12, "tax_amount": 140,
		"parentfield": "other_charges"
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Previous Row Amount",
		"account_head": "Education Cess - %s" % abbr, "rate": 2, "row_id": 3, "tax_amount": 2.8,
		"parentfield": "other_charges"
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Previous Row Amount",
		"account_head": "S&H Education Cess - %s" % abbr, "rate": 1, "row_id": 3, 
		"tax_amount": 1.4, "parentfield": "other_charges"
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Previous Row Total",
		"account_head": "CST - %s" % abbr, "rate": 2, "row_id": 5, "tax_amount": 32.38,
		"parentfield": "other_charges",
		"cost_center_other_charges": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "VAT - Test - %s" % abbr, "rate": 12.5, "tax_amount": 156.25,
		"parentfield": "other_charges"
	},
	{
		"doctype": "Sales Taxes and Charges", "charge_type": "On Previous Row Total",
		"account_head": "adj_rate - %s" % abbr, "rate": -10, "row_id": 7, "tax_amount": -180.78,
		"parentfield": "other_charges",
		"cost_center_other_charges": "Default Cost Center - %s" % abbr
	},
]

class TestSalesInvoice(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		load_data()
		#webnotes.conn.set_value("Global Defaults", None, "automatic_inventory_accounting", 1)

	def test_sales_invoice(self):
		doclist = [] + [d.copy() for d in sales_invoice_doclist]
		controller = webnotes.insert(DocList(doclist))
		controller.submit()
		controller.load_from_db()
		dl = controller.doclist

		# test net total
		self.assertEqual(dl[0].net_total, 1250)
		
		# test item values calculation
		expected_values = [
			{
				"item_code": "Home Desktop 100",
				# "ref_rate": 50,
				# "adj_rate": 0,
				# "export_amount": 500,
				# "base_ref_rate": 50,
				"basic_rate": 50,
				"amount": 500
			},
			{
				"item_code": "Home Desktop 200",
				# "ref_rate": 150,
				# "adj_rate": 0,
				# "export_amount": 750,
				# "base_ref_rate": 150,
				"basic_rate": 150,
				"amount": 750
			},
		]
		for i, item in enumerate(dl.get({"parentfield": "entries"})):
			for key, val in expected_values[i].items():
				self.assertEqual(item.fields.get(key), val)
		
		# test tax amounts and totals
		expected_values = [
			["Shipping Charges - %s" % abbr, 100, 1350],
			["Customs Duty - %s" % abbr, 125, 1475],
			["Excise Duty - %s" % abbr, 140, 1615],
			["Education Cess - %s" % abbr, 2.8, 1617.8],
			["S&H Education Cess - %s" % abbr, 1.4, 1619.2],
			["CST - %s" % abbr, 32.38, 1651.58],
			["VAT - Test - %s" % abbr, 156.25, 1807.83],
			["adj_rate - %s" % abbr, -180.78, 1627.05],
		]		
		for i, tax in enumerate(dl.get({"parentfield": "other_charges"})):
			# print tax.account_head, tax.tax_amount, tax.total
			self.assertEqual(tax.account_head, expected_values[i][0])
			self.assertEqual(tax.tax_amount, expected_values[i][1])
			# self.assertEqual(tax.total, expected_values[i][2])
			
		expected_gl_entries = {
			"West Wind Inc. - %s" % abbr : [1627.05, 0.0],
			"Sales - %s" % abbr: [0.0, 1250.00],
			"Shipping Charges - %s" % abbr: [0.0, 100],
			"Customs Duty - %s" % abbr: [0, 125.0],
			"Excise Duty - %s" % abbr: [0, 140],
			"Education Cess - %s" % abbr: [0, 2.8],
			"S&H Education Cess - %s" % abbr: [0, 1.4],
			"CST - %s" % abbr: [0, 32.38],
			"VAT - Test - %s" % abbr: [0, 156.25],
			"adj_rate - %s" % abbr: [180.78, 0],
		}
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type = %s and voucher_no = %s""", 
			(controller.doc.doctype, controller.doc.name), as_dict=1)
		
		for gle in gl_entries:
			self.assertEqual([gle.debit, gle.credit], expected_gl_entries[gle.account])
		
		# 	
		# def test_inclusive_rate_validations(self):
		# 	doclist = [] + [d.copy() for d in sales_invoice_doclist]
		# 	doclist[1]["export_rate"] = 62.5
		# 	doclist[2]["export_rate"] = 191
		# 	for i in [3, 5, 6, 7, 8, 9]:
		# 		doclist[i]["included_in_print_rate"] = 1
		# 	
		# 	# tax type "Actual" cannot be inclusive
		# 	self.assertRaises(webnotes.ValidationError, webnotes.insert,
		# 		DocList(doclist))
		# 	
		# 	doclist[3]["included_in_print_rate"] = 0
		# 	# taxes above included type 'On Previous Row Total' should also be included
		# 	self.assertRaises(webnotes.ValidationError, webnotes.insert,
		# 		DocList(doclist))
		# 
		# def test_sales_invoice_with_inclusive_tax(self):
		# 	doclist = [
		# 		# parent
		# 		{
		# 			"doctype": "Sales Invoice", 
		# 			"debit_to": "West Wind Inc. - %s" % abbr,
		# 			"customer_name": "West Wind Inc.",
		# 			"naming_series": "INV", "posting_date": nowdate(),
		# 			"company": company,
		# 			"fiscal_year": webnotes.conn.get_default("fiscal_year"), 
		# 			"currency": webnotes.conn.get_default("currency"),
		# 			"price_list_currency": webnotes.conn.get_default("currency"),
		# 			"conversion_rate": 1.0, "plc_conversion_rate": 1.0,
		# 			"grand_total_export": 0
		# 		},
		# 		# items
		# 		{
		# 			"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		# 			"item_code": "Home Desktop 100", "qty": 10, "export_rate": 62.503,
		# 			"parentfield": "entries",
		# 			"uom": "Nos", "item_tax_rate": json.dumps({"Excise Duty - %s" % abbr: 10})
		# 		},
		# 		{
		# 			"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		# 			"item_code": "Home Desktop 200", "qty": 5, "export_rate": 190.6608,
		# 			"parentfield": "entries",
		# 			"uom": "Nos"
		# 		},
		# 		# taxes
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "Excise Duty - %s" % abbr, "rate": 12,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Amount",
		# 			"account_head": "Education Cess - %s" % abbr, "rate": 2, "row_id": 1,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Amount",
		# 			"account_head": "S&H Education Cess - %s" % abbr, "rate": 1, "row_id": 1,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", 
		# 			"charge_type": "On Previous Row Total",
		# 			"account_head": "CST - %s" % abbr, "rate": 2, "row_id": 3,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1,
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "VAT - Test - %s" % abbr, "rate": 12.5,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "Customs Duty - %s" % abbr, "rate": 10,
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "Actual",
		# 			"account_head": "Shipping Charges - %s" % abbr, "rate": 100, 
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Total",
		# 			"account_head": "adj_rate - %s" % abbr, "rate": -10, "row_id": 7,
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 	]
		# 	
		# 	controller = webnotes.insert(DocList(doclist))
		# 	controller.load_from_db()
		# 	
		# 	from controllers.tax_controller import TaxController
		# 	tax_controller = TaxController(controller.doc, controller.doclist)
		# 	tax_controller.item_table_field = "entries"
		# 	tax_controller.calculate_taxes_and_totals()
		# 	
		# 	controller.doc = tax_controller.doc
		# 	controller.doclist = tax_controller.doclist
		# 	
		# 	controller.save()
		# 	controller.load_from_db()
		# 	dl = controller.doclist
		# 
		# 	# test item values calculation
		# 	expected_values = [
		# 		{
		# 			"item_code": "Home Desktop 100",
		# 			"ref_rate": 62.503,
		# 			"adj_rate": 0,
		# 			"export_amount": 625.03,
		# 			"base_ref_rate": 50,
		# 			"basic_rate": 50,
		# 			"amount": 500
		# 		},
		# 		{
		# 			"item_code": "Home Desktop 200",
		# 			"ref_rate": 190.6608,
		# 			"adj_rate": 0,
		# 			"export_amount": 953.3,
		# 			"base_ref_rate": 150,
		# 			"basic_rate": 150,
		# 			"amount": 750
		# 		},
		# 	]
		# 	for i, item in enumerate(dl.get({"parentfield": "entries"})):
		# 		for key, val in expected_values[i].items():
		# 			self.assertEqual(item.fields.get(key), val)
		# 	
		# 	# test tax amounts and totals
		# 	expected_values = [
		# 		["Excise Duty - %s" % abbr, 140, 1390, 0, 1578.33],
		# 		["Education Cess - %s" % abbr, 2.8, 1392.8, 0, 1578.33],
		# 		["S&H Education Cess - %s" % abbr, 1.4, 1394.2, 0, 1578.33],
		# 		["CST - %s" % abbr, 27.88, 1422.08, 0, 1578.33],
		# 		["VAT - Test - %s" % abbr, 156.25, 1578.33, 0, 1578.33],
		# 		["Customs Duty - %s" % abbr, 125, 1703.33, 125, 1703.33],
		# 		["Shipping Charges - %s" % abbr, 100, 1803.33, 100, 1803.33],
		# 		["adj_rate - %s" % abbr, -180.33, 1623, -180.33, 1623],
		# 	]		
		# 	for i, tax in enumerate(dl.get({"parentfield": "other_charges"})):
		# 		# print tax.account_head, tax.tax_amount, tax.total, tax.tax_amount_print, \
		# 		# 	tax.total_print
		# 		self.assertEqual(tax.account_head, expected_values[i][0])
		# 		self.assertEqual(tax.tax_amount, expected_values[i][1])
		# 		self.assertEqual(tax.total, expected_values[i][2])
		# 		# self.assertEqual(tax.tax_amount_print, expected_values[i][3])
		# 		self.assertEqual(tax.total_print, expected_values[i][4])
		# 		
		# 	# test net total
		# 	self.assertEqual(dl[0].net_total, 1250)
		# 
		# 	# # test grand total
		# 	self.assertEqual(dl[0].grand_total, 1623)
		# 	self.assertEqual(dl[0].grand_total_export, 1623)
		# 	
		# def test_usd_sales_invoice_with_inclusive_tax(self):
		# 	# print
		# 	# print "-"*80
		# 	# print "test_usd_sales_invoice_with_inclusive_tax"
		# 	# print "-"*80
		# 	
		# 	# Note: below values were obtained through manual calculation and verified by test
		# 	
		# 	doclist = [
		# 		# parent
		# 		{
		# 			"doctype": "Sales Invoice", 
		# 			"debit_to": "West Wind Inc. - %s" % abbr,
		# 			"customer_name": "West Wind Inc.",
		# 			"naming_series": "INV", "posting_date": nowdate(),
		# 			"company": company,
		# 			"fiscal_year": webnotes.conn.get_default("fiscal_year"), 
		# 			"currency": "USD", "price_list_currency": "USD", "conversion_rate": 50.0,
		# 			"plc_conversion_rate": 50.0, "grand_total_export": 0
		# 		},
		# 		# items
		# 		{
		# 			"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		# 			"item_code": "Home Desktop 100", "qty": 10, "export_rate": 50,
		# 			"adj_rate": 10, "parentfield": "entries",
		# 			"uom": "Nos", "item_tax_rate": json.dumps({"Excise Duty - %s" % abbr: 10})
		# 		},
		# 		{
		# 			"doctype": "Sales Invoice Item", "warehouse": "Default Warehouse",
		# 			"item_code": "Home Desktop 200", "qty": 5, "export_rate": 150,
		# 			"adj_rate": 20, "parentfield": "entries",
		# 			"uom": "Nos"
		# 		},
		# 		# taxes
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "Excise Duty - %s" % abbr, "rate": 12,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Amount",
		# 			"account_head": "Education Cess - %s" % abbr, "rate": 2, "row_id": 1,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Amount",
		# 			"account_head": "S&H Education Cess - %s" % abbr, "rate": 1, "row_id": 1,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", 
		# 			"charge_type": "On Previous Row Total",
		# 			"account_head": "CST - %s" % abbr, "rate": 2, "row_id": 3,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1,
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "VAT - Test - %s" % abbr, "rate": 12.5,
		# 			"parentfield": "other_charges", "included_in_print_rate": 1
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "On Net Total",
		# 			"account_head": "Customs Duty - %s" % abbr, "rate": 10,
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges", "charge_type": "Actual",
		# 			"account_head": "Shipping Charges - %s" % abbr, "rate": 100, 
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 		{
		# 			"doctype": "Sales Taxes and Charges",
		# 			"charge_type": "On Previous Row Total",
		# 			"account_head": "adj_rate - %s" % abbr, "rate": -10, "row_id": 7,
		# 			"parentfield": "other_charges",
		# 			"cost_center_other_charges": "Default Cost Center - %s" % abbr
		# 		},
		# 	]
		# 	
		# 	controller = webnotes.insert(DocList(doclist))
		# 	controller.load_from_db()
		# 	
		# 	from controllers.tax_controller import TaxController
		# 	tax_controller = TaxController(controller.doc, controller.doclist)
		# 	tax_controller.item_table_field = "entries"
		# 	tax_controller.calculate_taxes_and_totals()
		# 	
		# 	controller.doc = tax_controller.doc
		# 	controller.doclist = tax_controller.doclist
		# 	
		# 	controller.save()
		# 	controller.load_from_db()
		# 	dl = controller.doclist
		# 
		# 	# test item values calculation
		# 	expected_values = [
		# 		{
		# 			"item_code": "Home Desktop 100",
		# 			"ref_rate": 55.5556,
		# 			"adj_rate": 10,
		# 			"export_amount": 500,
		# 			"base_ref_rate": 2222.1156,
		# 			"basic_rate": 1999.904,
		# 			"amount": 19999.04
		# 		},
		# 		{
		# 			"item_code": "Home Desktop 200",
		# 			"ref_rate": 187.5,
		# 			"adj_rate": 20,
		# 			"export_amount": 750,
		# 			"base_ref_rate": 7375.664,
		# 			"basic_rate": 5900.5312,
		# 			"amount": 29502.66
		# 		},
		# 	]
		# 	for i, item in enumerate(dl.get({"parentfield": "entries"})):
		# 		for key, val in expected_values[i].items():
		# 			self.assertEqual(item.fields.get(key), val)
		# 	
		# 	# test tax amounts and totals
		# 	expected_values = [
		# 		["Excise Duty - %s" % abbr, 5540.22, 55041.92, 0, 1250],
		# 		["Education Cess - %s" % abbr, 110.81, 55152.73, 0, 1250],
		# 		["S&H Education Cess - %s" % abbr, 55.4, 55208.13, 0, 1250],
		# 		["CST - %s" % abbr, 1104.16, 56312.29, 0, 1250],
		# 		["VAT - Test - %s" % abbr, 6187.71, 62500, 0, 1250],
		# 		["Customs Duty - %s" % abbr, 4950.17, 67450.17, 99.01, 1349.01],
		# 		["Shipping Charges - %s" % abbr, 5000, 72450.17, 100, 1449.01],
		# 		["adj_rate - %s" % abbr, -7245.01, 65205.16, -144.9, 1304.11],
		# 	]		
		# 	for i, tax in enumerate(dl.get({"parentfield": "other_charges"})):
		# 		# print tax.account_head, tax.tax_amount, tax.total, tax.tax_amount_print, \
		# 		# 	tax.total_print
		# 		self.assertEqual(tax.account_head, expected_values[i][0])
		# 		self.assertEqual(tax.tax_amount, expected_values[i][1])
		# 		self.assertEqual(tax.total, expected_values[i][2])
		# 		# self.assertEqual(tax.tax_amount_print, expected_values[i][3])
		# 		self.assertEqual(tax.total_print, expected_values[i][4])
		# 		
		# 	# test net total
		# 	self.assertEqual(dl[0].net_total, 49501.7)
		# 
		# 	# # test grand total
		# 	self.assertEqual(dl[0].grand_total, 65205.16)
		# 	self.assertEqual(dl[0].grand_total_export, 1304.11)
		# 	

	def tearDown(self):
		webnotes.conn.rollback()