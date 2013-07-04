import webnotes
from webnotes.utils import flt
import unittest

test_dependencies = ["Sales BOM"]

class TestLead(unittest.TestCase):
	def test_make_sales_order(self):
		lead = webnotes.bean("Lead", "_T-Lead-00001")
		lead.make_controller()
		customer = lead.controller.make_customer()
		self.assertEquals(customer[0].doctype, "Customer")
		self.assertEquals(customer[0].lead_name, lead.doc.name)
		webnotes.bean(customer).insert()


test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"customer": "_Test Customer", 
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group", 
			"doctype": "Quotation", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"order_type": "Sales",
			"plc_conversion_rate": 1.0, 
			"price_list_currency": "INR", 
			"price_list_name": "_Test Price List", 
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
			"basic_rate": 100.0,
			"export_rate": 100.0,
			"amount": 1000.0,
		}
	],	
]