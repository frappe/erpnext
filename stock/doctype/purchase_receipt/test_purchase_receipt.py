# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.defaults
from webnotes.utils import cint

class TestPurchaseReceipt(unittest.TestCase):
	def test_make_purchase_invoice(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory(0)
		from stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pr = webnotes.bean(copy=test_records[0]).insert()
		
		self.assertRaises(webnotes.ValidationError, make_purchase_invoice, 
			pr.doc.name)

		pr = webnotes.bean("Purchase Receipt", pr.doc.name)
		pr.submit()
		pi = make_purchase_invoice(pr.doc.name)
		
		self.assertEquals(pi[0]["doctype"], "Purchase Invoice")
		self.assertEquals(len(pi), len(pr.doclist))
		
		# modify import_rate
		pi[1].import_rate = 200
		self.assertRaises(webnotes.ValidationError, webnotes.bean(pi).submit)
		
	def test_purchase_receipt_no_gl_entry(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory(0)
		pr = webnotes.bean(copy=test_records[0])
		pr.insert()
		pr.submit()
		
		stock_value, stock_value_difference = webnotes.conn.get_value("Stock Ledger Entry", 
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.doc.name, 
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}, 
			["stock_value", "stock_value_difference"])
		self.assertEqual(stock_value, 375)
		self.assertEqual(stock_value_difference, 375)
		
		bin_stock_value = webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")
		self.assertEqual(bin_stock_value, 375)
		
		self.assertFalse(get_gl_entries("Purchase Receipt", pr.doc.name))
		
	def test_purchase_receipt_gl_entry(self):
		self._clear_stock_account_balance()
		
		set_perpetual_inventory()
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_accounting_for_stock")), 1)
		
		pr = webnotes.bean(copy=test_records[0])
		pr.insert()
		pr.submit()
		
		gl_entries = get_gl_entries("Purchase Receipt", pr.doc.name)
		
		self.assertTrue(gl_entries)
		
		stock_in_hand_account = webnotes.conn.get_value("Account", 
			{"master_name": pr.doclist[1].warehouse})		
		fixed_asset_account = webnotes.conn.get_value("Account", 
			{"master_name": pr.doclist[2].warehouse})
		
		expected_values = {
			stock_in_hand_account: [375.0, 0.0],
			fixed_asset_account: [375.0, 0.0],
			"Stock Received But Not Billed - _TC": [0.0, 750.0]
		}
		
		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.debit)
			self.assertEquals(expected_values[gle.account][1], gle.credit)
			
		pr.cancel()
		self.assertFalse(get_gl_entries("Purchase Receipt", pr.doc.name))
		
		set_perpetual_inventory(0)
		
	def _clear_stock_account_balance(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("""delete from `tabGL Entry`""")
		
	def test_subcontracting(self):
		pr = webnotes.bean(copy=test_records[1])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		
		self.assertEquals(pr.doclist[1].rm_supp_cost, 70000.0)
		self.assertEquals(len(pr.doclist.get({"parentfield": "pr_raw_material_details"})), 2)
		
	def test_serial_no_supplier(self):
		pr = webnotes.bean(copy=test_records[0])
		pr.doclist[1].item_code = "_Test Serialized Item With Series"
		pr.doclist[1].qty = 1
		pr.doclist[1].received_qty = 1
		pr.insert()
		pr.submit()
		
		self.assertEquals(webnotes.conn.get_value("Serial No", pr.doclist[1].serial_no, 
			"supplier"), pr.doc.supplier)
			
		return pr
	
	def test_serial_no_cancel(self):
		pr = self.test_serial_no_supplier()
		pr.cancel()
		
		self.assertFalse(webnotes.conn.get_value("Serial No", pr.doclist[1].serial_no, 
			"warehouse"))
			
def get_gl_entries(voucher_type, voucher_no):
	return webnotes.conn.sql("""select account, debit, credit
		from `tabGL Entry` where voucher_type=%s and voucher_no=%s
		order by account desc""", (voucher_type, voucher_no), as_dict=1)
		
def set_perpetual_inventory(enable=1):
	accounts_settings = webnotes.bean("Accounts Settings")
	accounts_settings.doc.auto_accounting_for_stock = enable
	accounts_settings.save()
	
		
test_dependencies = ["BOM"]

test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"doctype": "Purchase Receipt", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"posting_date": "2013-02-12", 
			"posting_time": "15:33:30", 
			"supplier": "_Test Supplier",
			"net_total": 500.0, 
			"grand_total": 720.0,
			"naming_series": "_T-Purchase Receipt-",
		}, 
		{
			"conversion_factor": 1.0, 
			"description": "_Test Item", 
			"doctype": "Purchase Receipt Item", 
			"item_code": "_Test Item", 
			"item_name": "_Test Item", 
			"parentfield": "purchase_receipt_details", 
			"received_qty": 5.0,
			"qty": 5.0,
			"rejected_qty": 0.0,
			"import_rate": 50.0,
			"amount": 250.0,
			"warehouse": "_Test Warehouse - _TC", 
			"stock_uom": "Nos", 
			"uom": "_Test UOM",
		},
		{
			"conversion_factor": 1.0, 
			"description": "_Test Item", 
			"doctype": "Purchase Receipt Item", 
			"item_code": "_Test Item", 
			"item_name": "_Test Item", 
			"parentfield": "purchase_receipt_details", 
			"received_qty": 5.0,
			"qty": 5.0,
			"rejected_qty": 0.0,
			"import_rate": 50.0,
			"amount": 250.0,
			"warehouse": "_Test Warehouse 1 - _TC", 
			"stock_uom": "Nos", 
			"uom": "_Test UOM",
		},
		{
			"account_head": "_Test Account Shipping Charges - _TC", 
			"add_deduct_tax": "Add", 
			"category": "Valuation and Total", 
			"charge_type": "Actual", 
			"description": "Shipping Charges", 
			"doctype": "Purchase Taxes and Charges", 
			"parentfield": "purchase_tax_details",
			"rate": 100.0,
			"tax_amount": 100.0,
		},
		{
			"account_head": "_Test Account VAT - _TC", 
			"add_deduct_tax": "Add", 
			"category": "Total", 
			"charge_type": "Actual", 
			"description": "VAT", 
			"doctype": "Purchase Taxes and Charges", 
			"parentfield": "purchase_tax_details",
			"rate": 120.0,
			"tax_amount": 120.0,
		},
		{
			"account_head": "_Test Account Customs Duty - _TC", 
			"add_deduct_tax": "Add", 
			"category": "Valuation", 
			"charge_type": "Actual", 
			"description": "Customs Duty", 
			"doctype": "Purchase Taxes and Charges", 
			"parentfield": "purchase_tax_details",
			"rate": 150.0,
			"tax_amount": 150.0,
		},
	],
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"doctype": "Purchase Receipt", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"posting_date": "2013-02-12", 
			"posting_time": "15:33:30", 
			"is_subcontracted": "Yes",
			"supplier_warehouse": "_Test Warehouse - _TC", 
			"supplier": "_Test Supplier",
			"net_total": 5000.0, 
			"grand_total": 5000.0,
		}, 
		{
			"conversion_factor": 1.0, 
			"description": "_Test FG Item", 
			"doctype": "Purchase Receipt Item", 
			"item_code": "_Test FG Item", 
			"item_name": "_Test FG Item", 
			"parentfield": "purchase_receipt_details", 
			"received_qty": 10.0,
			"qty": 10.0,
			"rejected_qty": 0.0,
			"import_rate": 500.0,
			"amount": 5000.0,
			"warehouse": "_Test Warehouse - _TC", 
			"stock_uom": "Nos", 
			"uom": "_Test UOM",
		}
	],
]