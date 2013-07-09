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

class TestDeliveryNote(unittest.TestCase):
	def _insert_purchase_receipt(self):
		from stock.doctype.purchase_receipt.test_purchase_receipt import test_records as pr_test_records
		pr = webnotes.bean(copy=pr_test_records[0])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		pr.submit()
		
	def test_over_billing_against_dn(self):
		from stock.doctype.delivery_note.delivery_note import make_sales_invoice
		
		dn = webnotes.bean(copy=test_records[0]).insert()
		
		self.assertRaises(webnotes.ValidationError, make_sales_invoice, 
			dn.doc.name)

		dn = webnotes.bean("Delivery Note", dn.doc.name)
		dn.submit()
		si = make_sales_invoice(dn.doc.name)
		
		self.assertEquals(len(si), len(dn.doclist))
		
		# modify export_amount
		si[1].export_rate = 200
		self.assertRaises(webnotes.ValidationError, webnotes.bean(si).submit)
		
	
	def test_delivery_note_no_gl_entry(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_inventory_accounting")), 0)
		
		self._insert_purchase_receipt()
		
		dn = webnotes.bean(copy=test_records[0])
		dn.insert()
		dn.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Delivery Note' and voucher_no=%s
			order by account desc""", dn.doc.name, as_dict=1)
			
		self.assertTrue(not gl_entries)
		
	def test_delivery_note_gl_entry(self):
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_inventory_accounting")), 1)
		
		self._insert_purchase_receipt()
		
		dn = webnotes.bean(copy=test_records[0])
		dn.doclist[1].expense_account = "Cost of Goods Sold - _TC"
		dn.doclist[1].cost_center = "Main - _TC"

		stock_in_hand_account = webnotes.conn.get_value("Company", dn.doc.company, 
			"stock_in_hand_account")
		
		from accounts.utils import get_balance_on
		prev_bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)

		dn.insert()
		dn.submit()
		
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Delivery Note' and voucher_no=%s
			order by account asc""", dn.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			[stock_in_hand_account, 0.0, 375.0],
			["Cost of Goods Sold - _TC", 375.0, 0.0]
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
		
		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account, dn.doc.posting_date)
		self.assertEquals(bal, prev_bal - 375.0)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

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
			"price_list_name": "_Test Price List", 
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
			"warehouse": "_Test Warehouse",
			"stock_uom": "No."
		}
	]
	
]