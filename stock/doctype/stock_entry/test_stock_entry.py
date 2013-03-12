# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest

class TestStockEntry(unittest.TestCase):
	def test_auto_material_request(self):
		webnotes.conn.sql("""delete from `tabMaterial Request Item`""")
		webnotes.conn.sql("""delete from `tabMaterial Request`""")

		st1 = webnotes.bean(copy=test_records[0])
		st1.insert()
		st1.submit()

		st2 = webnotes.bean(copy=test_records[1])
		st2.insert()
		st2.submit()
		
		mr_name = webnotes.conn.sql("""select parent from `tabMaterial Request Item`
			where item_code='_Test Item'""")
			
		self.assertTrue(mr_name)
		
	def test_material_receipt_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			[["_Test Item", "_Test Warehouse", 50.0]])
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

	def test_material_issue_gl_entry(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		mr = webnotes.bean(copy=test_records[0])
		mr.insert()
		mr.submit()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		self.check_stock_ledger_entries("Stock Entry", mr.doc.name, 
			[["_Test Item", "_Test Warehouse", 50.0]])
			
		self.check_gl_entries("Stock Entry", mr.doc.name, 
			sorted([
				[stock_in_hand_account, 5000.0, 0.0], 
				["Stock Adjustment - _TC", 0.0, 5000.0]
			])
		)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
	
	def check_stock_ledger_entries(self, voucher_type, voucher_no, expected_sle):
		# check stock ledger entries
		sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where voucher_type = %s and voucher_no = %s order by item_code, warehouse""", 
			(voucher_type, voucher_no), as_dict=1)
		self.assertTrue(sle)
		
		for i, sle in enumerate(sle):
			self.assertEquals(expected_sle[i][0], sle.item_code)
			self.assertEquals(expected_sle[i][1], sle.warehouse)
			self.assertEquals(expected_sle[i][2], sle.actual_qty)
		
	def check_gl_entries(self, voucher_type, voucher_no, expected_gl_entries):
		# check gl entries
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s 
			order by account asc, debit asc""", (voucher_type, voucher_no), as_dict=1)
		self.assertTrue(gl_entries)
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)

test_records = [
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Receipt"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 50.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 50.0, 
			"uom": "_Test UOM",
			"t_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:15", 
			"purpose": "Material Issue"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 40.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 40.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
		}, 
	],
	[
		{
			"company": "_Test Company", 
			"doctype": "Stock Entry", 
			"posting_date": "2013-01-25", 
			"posting_time": "17:14:24", 
			"purpose": "Material Transfer"
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item Home Desktop 100", 
			"parentfield": "mtn_details", 
			"incoming_rate": 100,
			"qty": 45.0, 
			"stock_uom": "_Test UOM", 
			"transfer_qty": 45.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
			"t_warehouse": "_Test Warehouse 1",
		}, 
		{
			"conversion_factor": 1.0, 
			"doctype": "Stock Entry Detail", 
			"item_code": "_Test Item Home Desktop 100", 
			"parentfield": "mtn_details", 
			"qty": 45.0, 
			"incoming_rate": 100,
			"stock_uom": "_Test UOM", 
			"transfer_qty": 45.0, 
			"uom": "_Test UOM",
			"s_warehouse": "_Test Warehouse",
			"t_warehouse": "_Test Warehouse 1",
		}
	]
]