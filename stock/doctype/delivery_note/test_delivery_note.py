# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.defaults
from webnotes.utils import cint
from stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries, set_perpetual_inventory, test_records as pr_test_records

def _insert_purchase_receipt(item_code=None):
	if not item_code:
		item_code = pr_test_records[0][1]["item_code"]
	
	pr = webnotes.bean(copy=pr_test_records[0])
	pr.doclist[1].item_code = item_code
	pr.insert()
	pr.submit()
	
class TestDeliveryNote(unittest.TestCase):
	def test_over_billing_against_dn(self):
		self.clear_stock_account_balance()
		_insert_purchase_receipt()
		
		from stock.doctype.delivery_note.delivery_note import make_sales_invoice
		_insert_purchase_receipt()
		dn = webnotes.bean(copy=test_records[0]).insert()
		
		self.assertRaises(webnotes.ValidationError, make_sales_invoice, 
			dn.doc.name)

		dn = webnotes.bean("Delivery Note", dn.doc.name)
		dn.submit()
		si = make_sales_invoice(dn.doc.name)
		
		self.assertEquals(len(si), len(dn.doclist))
		
		# modify export_amount
		si[1].export_rate = 200
		self.assertRaises(webnotes.ValidationError, webnotes.bean(si).insert)
		
	
	def test_delivery_note_no_gl_entry(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory(0)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_accounting_for_stock")), 0)
		
		_insert_purchase_receipt()
		
		dn = webnotes.bean(copy=test_records[0])
		dn.insert()
		dn.submit()
		
		stock_value, stock_value_difference = webnotes.conn.get_value("Stock Ledger Entry", 
			{"voucher_type": "Delivery Note", "voucher_no": dn.doc.name, 
				"item_code": "_Test Item"}, ["stock_value", "stock_value_difference"])
		self.assertEqual(stock_value, 0)
		self.assertEqual(stock_value_difference, -375)
			
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Delivery Note' and voucher_no=%s
			order by account desc""", dn.doc.name, as_dict=1)
			
		self.assertFalse(get_gl_entries("Delivery Note", dn.doc.name))
		
	def test_delivery_note_gl_entry(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_accounting_for_stock")), 1)
		webnotes.conn.set_value("Item", "_Test Item", "valuation_method", "FIFO")
		
		_insert_purchase_receipt()
		
		dn = webnotes.bean(copy=test_records[0])
		dn.doclist[1].expense_account = "Cost of Goods Sold - _TC"
		dn.doclist[1].cost_center = "Main - _TC"

		stock_in_hand_account = webnotes.conn.get_value("Account", 
			{"master_name": dn.doclist[1].warehouse})
		
		from accounts.utils import get_balance_on
		prev_bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)

		dn.insert()
		dn.submit()
		
		gl_entries = get_gl_entries("Delivery Note", dn.doc.name)
		self.assertTrue(gl_entries)
		expected_values = {
			stock_in_hand_account: [0.0, 375.0],
			"Cost of Goods Sold - _TC": [375.0, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))
		
		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)
		self.assertEquals(bal, prev_bal - 375.0)
				
		# back dated purchase receipt
		pr = webnotes.bean(copy=pr_test_records[0])
		pr.doc.posting_date = "2013-01-01"
		pr.doclist[1].import_rate = 100
		pr.doclist[1].amount = 100
		
		pr.insert()
		pr.submit()
		
		gl_entries = get_gl_entries("Delivery Note", dn.doc.name)
		self.assertTrue(gl_entries)
		expected_values = {
			stock_in_hand_account: [0.0, 666.65],
			"Cost of Goods Sold - _TC": [666.65, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))
					
		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.doc.name))
		set_perpetual_inventory(0)
			
	def test_delivery_note_gl_entry_packing_item(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		
		_insert_purchase_receipt()
		_insert_purchase_receipt("_Test Item Home Desktop 100")
		
		dn = webnotes.bean(copy=test_records[0])
		dn.doclist[1].item_code = "_Test Sales BOM Item"
		dn.doclist[1].qty = 1
	
		stock_in_hand_account = webnotes.conn.get_value("Account", 
			{"master_name": dn.doclist[1].warehouse})
		
		from accounts.utils import get_balance_on
		prev_bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)
	
		dn.insert()
		dn.submit()
		
		gl_entries = get_gl_entries("Delivery Note", dn.doc.name)
		self.assertTrue(gl_entries)
		
		expected_values = {
			stock_in_hand_account: [0.0, 525],
			"Cost of Goods Sold - _TC": [525.0, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))
					
		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)
		self.assertEquals(bal, prev_bal - 525.0)
		
		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.doc.name))
		
		set_perpetual_inventory(0)
		
	def test_serialized(self):
		from stock.doctype.stock_entry.test_stock_entry import make_serialized_item
		from stock.doctype.serial_no.serial_no import get_serial_nos
		
		se = make_serialized_item()
		serial_nos = get_serial_nos(se.doclist[1].serial_no)
		
		dn = webnotes.bean(copy=test_records[0])
		dn.doclist[1].item_code = "_Test Serialized Item With Series"
		dn.doclist[1].qty = 1
		dn.doclist[1].serial_no = serial_nos[0]
		dn.insert()
		dn.submit()
		
		self.assertEquals(webnotes.conn.get_value("Serial No", serial_nos[0], "status"), "Delivered")
		self.assertFalse(webnotes.conn.get_value("Serial No", serial_nos[0], "warehouse"))
		self.assertEquals(webnotes.conn.get_value("Serial No", serial_nos[0], 
			"delivery_document_no"), dn.doc.name)
			
		return dn
			
	def test_serialized_cancel(self):
		from stock.doctype.serial_no.serial_no import get_serial_nos
		dn = self.test_serialized()
		dn.cancel()

		serial_nos = get_serial_nos(dn.doclist[1].serial_no)

		self.assertEquals(webnotes.conn.get_value("Serial No", serial_nos[0], "status"), "Available")
		self.assertEquals(webnotes.conn.get_value("Serial No", serial_nos[0], "warehouse"), "_Test Warehouse - _TC")
		self.assertFalse(webnotes.conn.get_value("Serial No", serial_nos[0], 
			"delivery_document_no"))

	def test_serialize_status(self):
		from stock.doctype.serial_no.serial_no import SerialNoStatusError, get_serial_nos
		from stock.doctype.stock_entry.test_stock_entry import make_serialized_item
		
		se = make_serialized_item()
		serial_nos = get_serial_nos(se.doclist[1].serial_no)
		
		sr = webnotes.bean("Serial No", serial_nos[0])
		sr.doc.status = "Not Available"
		sr.save()
		
		dn = webnotes.bean(copy=test_records[0])
		dn.doclist[1].item_code = "_Test Serialized Item With Series"
		dn.doclist[1].qty = 1
		dn.doclist[1].serial_no = serial_nos[0]
		dn.insert()

		self.assertRaises(SerialNoStatusError, dn.submit)
		
	def clear_stock_account_balance(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("delete from `tabGL Entry`")

test_dependencies = ["Sales BOM"]

test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"customer": "_Test Customer", 
			"customer_name": "_Test Customer",
			"doctype": "Delivery Note", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"plc_conversion_rate": 1.0, 
			"posting_date": "2013-02-21", 
			"posting_time": "9:00:00", 
			"price_list_currency": "INR", 
			"selling_price_list": "_Test Price List", 
			"status": "Draft", 
			"territory": "_Test Territory",
			"net_total": 500.0,
			"grand_total": 500.0, 
			"grand_total_export": 500.0,
			"naming_series": "_T-Delivery Note-"
		}, 
		{
			"description": "CPU", 
			"doctype": "Delivery Note Item", 
			"item_code": "_Test Item", 
			"item_name": "_Test Item", 
			"parentfield": "delivery_note_details", 
			"qty": 5.0, 
			"basic_rate": 100.0,
			"export_rate": 100.0,
			"amount": 500.0,
			"warehouse": "_Test Warehouse - _TC",
			"stock_uom": "_Test UOM",
			"expense_account": "Cost of Goods Sold - _TC",
			"cost_center": "Main - _TC"
		}
	]
	
]
