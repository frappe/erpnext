# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest

class TestSerialNo(unittest.TestCase):
	def test_aii_gl_entries_for_serial_no_in_store(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		sr = webnotes.bean(copy=test_records[0])
		sr.doc.serial_no = "_Test Serial No 1"
		sr.insert()
		
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		against_stock_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_adjustment_account")
		
		# check stock ledger entries
		sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where voucher_type = 'Serial No' and voucher_no = %s""", sr.doc.name, as_dict=1)[0]
		self.assertTrue(sle)
		self.assertEquals([sle.item_code, sle.warehouse, sle.actual_qty], 
			["_Test Serialized Item", "_Test Warehouse", 1.0])
			
		# check gl entries
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Serial No' and voucher_no=%s
			order by account desc""", sr.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = [
			[stock_in_hand_account, 1000.0, 0.0],
			[against_stock_account, 0.0, 1000.0]
		]
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
		
		sr.load_from_db()
		self.assertEquals(sr.doc.sle_exists, 1)
		
		# save again	
		sr.save()
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Serial No' and voucher_no=%s
			order by account desc""", sr.doc.name, as_dict=1)
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
			
		# trash/cancel
		sr.submit()
		sr.cancel()
		
		gl_count = webnotes.conn.sql("""select count(name) from `tabGL Entry` 
			where voucher_type='Serial No' and voucher_no=%s and ifnull(is_cancelled, 'No') = 'Yes' 
			order by account asc, name asc""", sr.doc.name)
		
		self.assertEquals(gl_count[0][0], 4)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		
		
	def test_aii_gl_entries_for_serial_no_delivered(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		sr = webnotes.bean(copy=test_records[0])
		sr.doc.serial_no = "_Test Serial No 2"
		sr.doc.status = "Delivered"
		sr.insert()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Serial No' and voucher_no=%s
			order by account desc""", sr.doc.name, as_dict=1)
		self.assertFalse(gl_entries)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

test_dependencies = ["Item"]
test_records = [
	[
		{
			"company": "_Test Company", 
			"doctype": "Serial No", 
			"serial_no": "_Test Serial No", 
			"status": "In Store",
			"item_code": "_Test Serialized Item", 
			"item_group": "_Test Item Group", 
			"warehouse": "_Test Warehouse",
			"purchase_rate": 1000.0, 
			"purchase_time": "11:37:39", 
			"purchase_date": "2013-02-26",
			'fiscal_year': "_Test Fiscal Year 2013"
		}
	]
]