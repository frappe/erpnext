# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.defaults
from webnotes.utils import cint

class TestPurchaseReceipt(unittest.TestCase):
	def test_make_purchase_invoice(self):
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
		pr = webnotes.bean(copy=test_records[0])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		pr.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Receipt' and voucher_no=%s
			order by account desc""", pr.doc.name, as_dict=1)
			
		self.assertTrue(not gl_entries)
		
	def test_purchase_receipt_gl_entry(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_inventory_accounting")), 1)
		
		pr = webnotes.bean(copy=test_records[0])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		pr.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Receipt' and voucher_no=%s
			order by account desc""", pr.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		stock_in_hand_account = webnotes.conn.get_value("Company", pr.doc.company, 
			"stock_in_hand_account")
		
		expected_values = [
			[stock_in_hand_account, 750.0, 0.0],
			["Stock Received But Not Billed - _TC", 0.0, 750.0]
		]
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
			
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		
	def test_subcontracting(self):
		pr = webnotes.bean(copy=test_records[1])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		
		self.assertEquals(pr.doclist[1].rm_supp_cost, 70000.0)
		self.assertEquals(len(pr.doclist.get({"parentfield": "pr_raw_material_details"})), 2)


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
			"received_qty": 10.0,
			"qty": 10.0,
			"rejected_qty": 0.0,
			"import_rate": 50.0,
			"amount": 500.0,
			"warehouse": "_Test Warehouse", 
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
			"supplier_warehouse": "_Test Warehouse", 
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
			"warehouse": "_Test Warehouse", 
			"stock_uom": "Nos", 
			"uom": "_Test UOM",
		}
	],
]