import webnotes
import unittest

class TestSalesInvoice(unittest.TestCase):
	def make(self):
		w = webnotes.model_wrapper(webnotes.copy_doclist(test_records[0]))
		w.insert()
		w.submit()
		return w

	def test_outstanding(self):
		w = self.make()
		self.assertEquals(w.doc.outstanding_amount, w.doc.grand_total)
		
	def test_payment(self):
		w = self.make()
		from accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records
			
		jv = webnotes.model_wrapper(webnotes.copy_doclist(jv_test_records[0]))
		jv.doclist[1].against_invoice = w.doc.name
		jv.insert()
		jv.submit()
		
		self.assertEquals(webnotes.conn.get_value("Sales Invoice", w.doc.name, "outstanding_amount"),
			161.8)
	
		jv.cancel()
		self.assertEquals(webnotes.conn.get_value("Sales Invoice", w.doc.name, "outstanding_amount"),
			561.8)
		
test_dependencies = ["Journal Voucher"]

test_records = [[
	{
		"naming_series": "_T-Sales Invoice-",
		"company": "_Test Company", 
		"conversion_rate": 1.0, 
		"currency": "INR", 
		"debit_to": "_Test Customer - _TC",
		"customer": "_Test Customer",
		"customer_name": "_Test Customer",
		"doctype": "Sales Invoice", 
		"due_date": "2013-01-23", 
		"fiscal_year": "_Test Fiscal Year 2013", 
		"grand_total": 561.8, 
		"grand_total_export": 561.8, 
		"net_total": 500.0, 
		"plc_conversion_rate": 1.0, 
		"posting_date": "2013-01-23", 
		"price_list_currency": "INR", 
		"price_list_name": "_Test Price List", 
		"territory": "_Test Territory"
	}, 
	{
		"amount": 500.0, 
		"basic_rate": 500.0, 
		"description": "138-CMS Shoe", 
		"doctype": "Sales Invoice Item", 
		"export_amount": 500.0, 
		"export_rate": 500.0, 
		"income_account": "Sales - _TC",
		"cost_center": "_Test Cost Center - _TC",
		"item_name": "138-CMS Shoe", 
		"parentfield": "entries",
		"qty": 1.0
	}, 
	{
		"account_head": "_Test Account VAT - _TC", 
		"charge_type": "On Net Total", 
		"description": "VAT", 
		"doctype": "Sales Taxes and Charges", 
		"parentfield": "other_charges",
		"tax_amount": 30.0,
	}, 
	{
		"account_head": "_Test Account Service Tax - _TC", 
		"charge_type": "On Net Total", 
		"description": "Service Tax", 
		"doctype": "Sales Taxes and Charges", 
		"parentfield": "other_charges",
		"tax_amount": 31.8,
	}
]]