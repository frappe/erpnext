import webnotes
from webnotes.utils import flt
import unittest

class TestSalesOrder(unittest.TestCase):
	def make(self):
		w = webnotes.model_wrapper(webnotes.copy_doclist(test_records[0]))
		w.insert()
		w.submit()
		return w
		
	def get_bin_reserved_qty(self, item_code, warehouse):
		return flt(webnotes.conn.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, 
			"reserved_qty"))
		
	def test_reserved_qty_so_submit_cancel(self):		
		# submit
		so = self.make()
		print self.get_bin_reserved_qty(so.doclist[1].item_code, 
			so.doclist[1].reserved_warehouse)

		reserved_qty = self.get_bin_reserved_qty(so.doclist[1].item_code, 
			so.doclist[1].reserved_warehouse)
		self.assertEqual(reserved_qty, 10.0)
		# cancel
		so.cancel()
		reserved_qty = self.get_bin_reserved_qty(so.doclist[1].item_code, 
			so.doclist[1].reserved_warehouse)
		self.assertEqual(reserved_qty, 0.0)
	
	def test_reserved_qty_dn_submit_cancel(self):
		so = self.make()
		
		# allow negative stock
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		# dn submit (against so)
		from stock.doctype.delivery_note.test_delivery_note import test_records as dn_test_records
		dn = webnotes.model_wrapper(webnotes.copy_doclist(dn_test_records[0]))
		dn.doclist[1].prevdoc_doctype = "Sales Order"
		dn.doclist[1].prevdoc_docname = so.doc.name
		dn.doclist[1].prevdoc_detail_docname = so.doclist[1].name
		dn.insert()
		dn.submit()
		
		reserved_qty = self.get_bin_reserved_qty(so.doclist[1].item_code, 
			so.doclist[1].reserved_warehouse)
		self.assertEqual(reserved_qty, 6.0)
		
test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"customer": "_Test Customer", 
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group", 
			"doctype": "Sales Order", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"order_type": "Sales",
			"delivery_date": "2013-02-23",
			"plc_conversion_rate": 1.0, 
			"price_list_currency": "INR", 
			"price_list_name": "_Test Price List", 
			"territory": "_Test Territory", 
			"transaction_date": "2013-02-21",
			"grand_total": 500.0, 
			"grand_total_export": 500.0, 
		}, 
		{
			"description": "CPU", 
			"doctype": "Sales Order Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"item_name": "CPU", 
			"parentfield": "sales_order_details", 
			"qty": 10.0,
			"basic_rate": 50.0,
			"export_rate": 50.0,
			"amount": 500.0,
			"reserved_warehouse": "_Test Warehouse",
		}
	]
]