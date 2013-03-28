# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest
from webnotes.utils import flt

class TestMaterialRequest(unittest.TestCase):
	def _test_expected(self, doclist, expected_values):
		for i, expected in enumerate(expected_values):
			for fieldname, val in expected.items():
				self.assertEquals(val, doclist[i].fields.get(fieldname))
				
	def _test_requested_qty(self, qty1, qty2):
		self.assertEqual(flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item Home Desktop 100",
			"warehouse": "_Test Warehouse"}, "indented_qty")), qty1)
		self.assertEqual(flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item Home Desktop 200",
			"warehouse": "_Test Warehouse"}, "indented_qty")), qty2)
			
	def _insert_stock_entry(self, qty1, qty2):
		se = webnotes.bean([
			{
				"company": "_Test Company", 
				"doctype": "Stock Entry", 
				"posting_date": "2013-03-01", 
				"posting_time": "00:00:00", 
				"purpose": "Material Receipt",
				"fiscal_year": "_Test Fiscal Year 2013",
			}, 
			{
				"conversion_factor": 1.0, 
				"doctype": "Stock Entry Detail", 
				"item_code": "_Test Item Home Desktop 100",
				"parentfield": "mtn_details", 
				"incoming_rate": 100,
				"qty": qty1, 
				"stock_uom": "_Test UOM", 
				"transfer_qty": qty1, 
				"uom": "_Test UOM",
				"t_warehouse": "_Test Warehouse 1",
			},
			{
				"conversion_factor": 1.0, 
				"doctype": "Stock Entry Detail", 
				"item_code": "_Test Item Home Desktop 200",
				"parentfield": "mtn_details", 
				"incoming_rate": 100,
				"qty": qty2, 
				"stock_uom": "_Test UOM", 
				"transfer_qty": qty2, 
				"uom": "_Test UOM",
				"t_warehouse": "_Test Warehouse 1",
			},
		])
		se.insert()
		se.submit()
				
	def test_completed_qty_for_purchase(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		# check if per complete is None
		self._test_expected(mr.doclist, [{"per_ordered": None}, {"ordered_qty": None}, {"ordered_qty": None}])
		
		self._test_requested_qty(54.0, 3.0)
		
		# map a purchase order
		po_doclist = webnotes.map_doclist([["Material Request", "Purchase Order"], 
			["Material Request Item", "Purchase Order Item"]], mr.doc.name)
		po_doclist[0].fields.update({
			"supplier": "_Test Supplier",
			"supplier_name": "_Test Supplier",
			"transaction_date": mr.doc.transaction_date,
			"fiscal_year": "_Test Fiscal Year 2013",
			"currency": "INR",
			"conversion_rate": 1.0,
			"grand_total_import": 0.0
		})
		po_doclist[1].qty = 27.0
		po_doclist[2].qty = 1.5
		
		# check for stopped status of Material Request
		po = webnotes.bean(copy=po_doclist)
		po.insert()
		mr.obj.update_status('Stopped')
		self.assertRaises(webnotes.ValidationError, po.submit)
		self.assertRaises(webnotes.ValidationError, po.cancel)

		mr.obj.update_status('Submitted')
		po = webnotes.bean(copy=po_doclist)
		po.insert()
		po.submit()
		
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 50}, {"ordered_qty": 27.0}, {"ordered_qty": 1.5}])
		self._test_requested_qty(27.0, 1.5)
		
		po.cancel()
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 0}, {"ordered_qty": 0}, {"ordered_qty": 0}])
		self._test_requested_qty(54.0, 3.0)
		
	def test_completed_qty_for_transfer(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("""delete from `tabStock Ledger Entry`""")
		
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.doc.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		self._test_expected(mr.doclist, [{"per_ordered": None}, {"ordered_qty": None}, {"ordered_qty": None}])
		
		self._test_requested_qty(54.0, 3.0)
		
		# map a stock entry
		se_doclist = webnotes.map_doclist([["Material Request", "Stock Entry"], 
			["Material Request Item", "Stock Entry Detail"]], mr.doc.name)
		se_doclist[0].fields.update({
			"posting_date": "2013-03-01",
			"posting_time": "01:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doclist[1].fields.update({
			"qty": 27.0,
			"transfer_qty": 27.0,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		se_doclist[2].fields.update({
			"qty": 1.5,
			"transfer_qty": 1.5,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		
		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(27.0, 1.5)
		
		# check for stopped status of Material Request
		se = webnotes.bean(copy=se_doclist)
		se.insert()
		mr.obj.update_status('Stopped')
		self.assertRaises(webnotes.ValidationError, se.submit)
		self.assertRaises(webnotes.ValidationError, se.cancel)
		
		mr.obj.update_status('Submitted')
		se = webnotes.bean(copy=se_doclist)
		se.insert()
		se.submit()
		
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 50}, {"ordered_qty": 27.0}, {"ordered_qty": 1.5}])
		self._test_requested_qty(27.0, 1.5)
		
		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 0}, {"ordered_qty": 0}, {"ordered_qty": 0}])
		self._test_requested_qty(54.0, 3.0)
		
	def test_completed_qty_for_over_transfer(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("""delete from `tabStock Ledger Entry`""")
		
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.doc.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# check if per complete is None
		self._test_expected(mr.doclist, [{"per_ordered": None}, {"ordered_qty": None}, {"ordered_qty": None}])
		
		self._test_requested_qty(54.0, 3.0)
		
		# map a stock entry
		se_doclist = webnotes.map_doclist([["Material Request", "Stock Entry"], 
			["Material Request Item", "Stock Entry Detail"]], mr.doc.name)
		se_doclist[0].fields.update({
			"posting_date": "2013-03-01",
			"posting_time": "00:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doclist[1].fields.update({
			"qty": 60.0,
			"transfer_qty": 60.0,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		se_doclist[2].fields.update({
			"qty": 3.0,
			"transfer_qty": 3.0,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})

		# make available the qty in _Test Warehouse 1 before transfer
		self._insert_stock_entry(60.0, 3.0)
		
		# check for stopped status of Material Request
		se = webnotes.bean(copy=se_doclist)
		se.insert()
		mr.obj.update_status('Stopped')
		self.assertRaises(webnotes.ValidationError, se.submit)
		self.assertRaises(webnotes.ValidationError, se.cancel)
		
		mr.obj.update_status('Submitted')
		se = webnotes.bean(copy=se_doclist)
		se.insert()
		se.submit()
		
		# check if per complete is as expected
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 100}, {"ordered_qty": 60.0}, {"ordered_qty": 3.0}])
		self._test_requested_qty(0.0, 0.0)
		
		# check if per complete is as expected for Stock Entry cancelled
		se.cancel()
		mr.load_from_db()
		self._test_expected(mr.doclist, [{"per_ordered": 0}, {"ordered_qty": 0}, {"ordered_qty": 0}])
		self._test_requested_qty(54.0, 3.0)
		
	def test_incorrect_mapping_of_stock_entry(self):
		# submit material request of type Purchase
		mr = webnotes.bean(copy=test_records[0])
		mr.doc.material_request_type = "Transfer"
		mr.insert()
		mr.submit()

		# map a stock entry
		se_doclist = webnotes.map_doclist([["Material Request", "Stock Entry"], 
			["Material Request Item", "Stock Entry Detail"]], mr.doc.name)
		se_doclist[0].fields.update({
			"posting_date": "2013-03-01",
			"posting_time": "00:00",
			"fiscal_year": "_Test Fiscal Year 2013",
		})
		se_doclist[1].fields.update({
			"qty": 60.0,
			"transfer_qty": 60.0,
			"s_warehouse": "_Test Warehouse",
			"t_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		se_doclist[2].fields.update({
			"qty": 3.0,
			"transfer_qty": 3.0,
			"s_warehouse": "_Test Warehouse 1",
			"incoming_rate": 1.0
		})
		
		# check for stopped status of Material Request
		se = webnotes.bean(copy=se_doclist)
		self.assertRaises(webnotes.MappingMismatchError, se.insert)
		
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
	],
]