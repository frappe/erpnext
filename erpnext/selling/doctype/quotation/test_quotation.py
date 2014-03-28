# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, json
from frappe.utils import flt
import unittest

test_dependencies = ["Sales BOM"]

class TestQuotation(unittest.TestCase):
	def test_make_sales_order(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		
		quotation = frappe.get_doc(copy=test_records[0])
		quotation.insert()
		
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
				
		self.assertEquals(sales_order[0]["doctype"], "Sales Order")
		self.assertEquals(len(sales_order), 2)
		self.assertEquals(sales_order[1]["doctype"], "Sales Order Item")
		self.assertEquals(sales_order[1]["prevdoc_docname"], quotation.name)
		self.assertEquals(sales_order[0]["customer"], "_Test Customer")
		
		sales_order[0]["delivery_date"] = "2014-01-01"
		sales_order[0]["naming_series"] = "_T-Quotation-"
		sales_order[0]["transaction_date"] = "2013-05-12"
		frappe.get_doc(sales_order).insert()


test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"quotation_to": "Customer",
			"customer": "_Test Customer", 
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group", 
			"doctype": "Quotation", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"order_type": "Sales",
			"plc_conversion_rate": 1.0, 
			"price_list_currency": "INR", 
			"selling_price_list": "_Test Price List", 
			"territory": "_Test Territory", 
			"transaction_date": "2013-02-21",
			"grand_total": 1000.0, 
			"grand_total_export": 1000.0, 
		}, 
		{
			"description": "CPU", 
			"doctype": "Quotation Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"item_name": "CPU", 
			"parentfield": "quotation_details", 
			"qty": 10.0,
			"base_rate": 100.0,
			"rate": 100.0,
			"base_amount": 1000.0,
		}
	],	
]