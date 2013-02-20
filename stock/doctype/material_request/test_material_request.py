# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest

class TestMaterialRequest(unittest.TestCase):
	def _test_expected(self, doclist, expected_values):
		for i, expected in enumerate(expected_values):
			for fieldname, val in expected.items():
				self.assertEquals(val, doclist[i].fields.get(fieldname))
				
	def test_completed_qty_for_purchase(self):
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		# check if per complete is None
		self._test_expected(mr.doclist, [{"per_ordered": None}, {"ordered_qty": None}, {"ordered_qty": None}])
		
		# map a purchase order
		po = webnotes.map_doclist([["Material Request", "Purchase Order"], 
			["Material Request Item", "Purchase Order Item"]], mr.doc.name)
		po = webnotes.bean(po)
		po.doc.fields.update({
			"supplier": "_Test Supplier",
			"supplier_name": "_Test Supplier",
			"transaction_date": mr.doc.transaction_date,
			"fiscal_year": "_Test Fiscal Year 2013",
			"currency": "INR",
			"conversion_rate": 1.0,
			"grand_total_import": 0.0
		})
		po.doclist[1].qty = 27.0
		po.doclist[2].qty = 1.5
		po.insert()
		po.submit()
		
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 50}, {"ordered_qty": 27.0}, {"ordered_qty": 1.5}])
		
		po.cancel()
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 0}, {"ordered_qty": 0}, {"ordered_qty": 0}])
		
	def test_completed_qty_for_transfer(self):
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.doc.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		self._test_expected(mr.doclist, [{"per_ordered": None}, {"ordered_qty": None}, {"ordered_qty": None}])
		
		# map a stock entry
		se = webnotes.map_doclist([["Material Request", "Stock Entry"], 
			["Material Request Item", "Stock Entry Detail"]], mr.doc.name)
		se = webnotes.bean(se)
		se.doc.fields.update({
			"posting_date": "2013-03-01",
			"posting_time": "00:00"
		})
		se.doclist[1].fields.update({
			"qty": 27.0,
			"transfer_qty": 27.0,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		se.doclist[2].fields.update({
			"qty": 1.5,
			"transfer_qty": 1.5,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		se.insert()
		se.submit()
		
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 50}, {"ordered_qty": 27.0}, {"ordered_qty": 1.5}])

test_records = [
	[
		{
			"company": "_Test Company", 
			"doctype": "Material Request", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"transaction_date": "2013-02-18",
			"material_request_type": "Purchase"
		}, 
		{
			"description": "_Test Item Home Desktop 100", 
			"doctype": "Material Request Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"item_name": "_Test Item Home Desktop 100", 
			"parentfield": "indent_details", 
			"qty": 54.0, 
			"schedule_date": "2013-02-18", 
			"uom": "_Test UOM",
			"warehouse": "_Test Warehouse"
		}, 
		{
			"description": "_Test Item Home Desktop 200", 
			"doctype": "Material Request Item", 
			"item_code": "_Test Item Home Desktop 200", 
			"item_name": "_Test Item Home Desktop 200", 
			"parentfield": "indent_details", 
			"qty": 3.0, 
			"schedule_date": "2013-02-19", 
			"uom": "_Test UOM",
			"warehouse": "_Test Warehouse"
		}
	]
]