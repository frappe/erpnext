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
import webnotes.model
import json	
from webnotes.utils import cint
import webnotes.defaults

test_dependencies = ["Item", "Cost Center"]
test_ignore = ["Serial No"]

class TestPurchaseInvoice(unittest.TestCase):
	def test_gl_entries_without_auto_inventory_accounting(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		self.assertTrue(not cint(webnotes.defaults.get_global_default("auto_inventory_accounting")))
		
		wrapper = webnotes.bean(copy=test_records[0])
		wrapper.run_method("calculate_taxes_and_totals")
		wrapper.insert()
		wrapper.submit()
		wrapper.load_from_db()
		dl = wrapper.doclist
		
		expected_gl_entries = {
			"_Test Supplier - _TC": [0, 1512.30],
			"_Test Account Cost for Goods Sold - _TC": [1250, 0],
			"_Test Account Shipping Charges - _TC": [100, 0],
			"_Test Account Excise Duty - _TC": [140, 0],
			"_Test Account Education Cess - _TC": [2.8, 0],
			"_Test Account S&H Education Cess - _TC": [1.4, 0],
			"_Test Account CST - _TC": [29.88, 0],
			"_Test Account VAT - _TC": [156.25, 0],
			"_Test Account Discount - _TC": [0, 168.03],
		}
		gl_entries = webnotes.conn.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type = 'Purchase Invoice' and voucher_no = %s""", dl[0].name, as_dict=1)
		for d in gl_entries:
			self.assertEqual([d.debit, d.credit], expected_gl_entries.get(d.account))
			
	def test_gl_entries_with_auto_inventory_accounting(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_inventory_accounting")), 1)
		
		pi = webnotes.bean(copy=test_records[1])
		pi.run_method("calculate_taxes_and_totals")
		pi.insert()
		pi.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			["_Test Supplier - _TC", 0, 720],
			["Stock Received But Not Billed - _TC", 750.0, 0],
			["_Test Account Shipping Charges - _TC", 100.0, 0],
			["_Test Account VAT - _TC", 120.0, 0],
			["Expenses Included In Valuation - _TC", 0, 250.0],
		])
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)

	def test_gl_entries_with_aia_for_non_stock_items(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		self.assertEqual(cint(webnotes.defaults.get_global_default("auto_inventory_accounting")), 1)
		
		pi = webnotes.bean(copy=test_records[1])
		pi.doclist[1].item_code = "_Test Non Stock Item"
		pi.doclist[1].expense_head = "_Test Account Cost for Goods Sold - _TC"
		pi.doclist.pop(2)
		pi.doclist.pop(3)
		pi.run_method("calculate_taxes_and_totals")
		pi.insert()
		pi.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			["_Test Supplier - _TC", 0, 620],
			["_Test Account Cost for Goods Sold - _TC", 500.0, 0],
			["_Test Account VAT - _TC", 120.0, 0],
		])
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
			
	def test_purchase_invoice_calculation(self):
		wrapper = webnotes.bean(copy=test_records[0])
		wrapper.run_method("calculate_taxes_and_totals")
		wrapper.insert()
		wrapper.load_from_db()
		
		expected_values = [
			["_Test Item Home Desktop 100", 90, 59],
			["_Test Item Home Desktop 200", 135, 177]
		]
		for i, item in enumerate(wrapper.doclist.get({"parentfield": "entries"})):
			self.assertEqual(item.item_code, expected_values[i][0])
			self.assertEqual(item.item_tax_amount, expected_values[i][1])
			self.assertEqual(item.valuation_rate, expected_values[i][2])
			
		self.assertEqual(wrapper.doclist[0].net_total, 1250)
		
		# tax amounts
		expected_values = [
			["_Test Account Shipping Charges - _TC", 100, 1350],
			["_Test Account Customs Duty - _TC", 125, 1350],
			["_Test Account Excise Duty - _TC", 140, 1490],
			["_Test Account Education Cess - _TC", 2.8, 1492.8],
			["_Test Account S&H Education Cess - _TC", 1.4, 1494.2],
			["_Test Account CST - _TC", 29.88, 1524.08],
			["_Test Account VAT - _TC", 156.25, 1680.33],
			["_Test Account Discount - _TC", 168.03, 1512.30],
		]
		
		for i, tax in enumerate(wrapper.doclist.get({"parentfield": "purchase_tax_details"})):
			self.assertEqual(tax.account_head, expected_values[i][0])
			self.assertEqual(tax.tax_amount, expected_values[i][1])
			self.assertEqual(tax.total, expected_values[i][2])
			
	def test_purchase_invoice_with_subcontracted_item(self):
		wrapper = webnotes.bean(copy=test_records[0])
		wrapper.doclist[1].item_code = "_Test FG Item"
		wrapper.run_method("calculate_taxes_and_totals")
		wrapper.insert()
		wrapper.load_from_db()
		
		expected_values = [
			["_Test FG Item", 90, 7059],
			["_Test Item Home Desktop 200", 135, 177]
		]
		for i, item in enumerate(wrapper.doclist.get({"parentfield": "entries"})):
			self.assertEqual(item.item_code, expected_values[i][0])
			self.assertEqual(item.item_tax_amount, expected_values[i][1])
			self.assertEqual(item.valuation_rate, expected_values[i][2])
		
		self.assertEqual(wrapper.doclist[0].net_total, 1250)

		# tax amounts
		expected_values = [
			["_Test Account Shipping Charges - _TC", 100, 1350],
			["_Test Account Customs Duty - _TC", 125, 1350],
			["_Test Account Excise Duty - _TC", 140, 1490],
			["_Test Account Education Cess - _TC", 2.8, 1492.8],
			["_Test Account S&H Education Cess - _TC", 1.4, 1494.2],
			["_Test Account CST - _TC", 29.88, 1524.08],
			["_Test Account VAT - _TC", 156.25, 1680.33],
			["_Test Account Discount - _TC", 168.03, 1512.30],
		]

		for i, tax in enumerate(wrapper.doclist.get({"parentfield": "purchase_tax_details"})):
			self.assertEqual(tax.account_head, expected_values[i][0])
			self.assertEqual(tax.tax_amount, expected_values[i][1])
			self.assertEqual(tax.total, expected_values[i][2])
			
	def test_purchase_invoice_with_advance(self):
		from accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records
			
		jv = webnotes.bean(copy=jv_test_records[1])
		jv.insert()
		jv.submit()
		
		pi = webnotes.bean(copy=test_records[0])
		pi.doclist.append({
			"doctype": "Purchase Invoice Advance",
			"parentfield": "advance_allocation_details",
			"journal_voucher": jv.doc.name,
			"jv_detail_no": jv.doclist[1].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.doc.remark
		})
		pi.run_method("calculate_taxes_and_totals")
		pi.insert()
		pi.submit()
		pi.load_from_db()
		
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_voucher=%s""", pi.doc.name))
		
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_voucher=%s and debit=300""", pi.doc.name))
			
		self.assertEqual(pi.doc.outstanding_amount, 1212.30)
		
		pi.cancel()
		
		self.assertTrue(not webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_voucher=%s""", pi.doc.name))
	
test_records = [
	[
		# parent
		{
			"doctype": "Purchase Invoice",
			"naming_series": "BILL",
			"supplier_name": "_Test Supplier",
			"credit_to": "_Test Supplier - _TC",
			"bill_no": "NA",
			"posting_date": "2013-02-03",
			"fiscal_year": "_Test Fiscal Year 2013",
			"company": "_Test Company",
			"currency": "INR",
			"conversion_rate": 1,
			"grand_total_import": 0 # for feed
		},
		# items
		{
			"doctype": "Purchase Invoice Item",
			"parentfield": "entries",
			"item_code": "_Test Item Home Desktop 100",
			"item_name": "_Test Item Home Desktop 100",
			"qty": 10,
			"import_rate": 50,
			"import_amount": 500,
			"rate": 50,
			"amount": 500,
			"uom": "_Test UOM",
			"item_tax_rate": json.dumps({"_Test Account Excise Duty - _TC": 10}),
			"expense_head": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"conversion_factor": 1.0,
		
		},
		{
			"doctype": "Purchase Invoice Item",
			"parentfield": "entries",
			"item_code": "_Test Item Home Desktop 200",
			"item_name": "_Test Item Home Desktop 200",
			"qty": 5,
			"import_rate": 150,
			"import_amount": 750,
			"rate": 150,
			"amount": 750,
			"uom": "_Test UOM",
			"expense_head": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"conversion_factor": 1.0,
		},
		# taxes
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "Actual",
			"account_head": "_Test Account Shipping Charges - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Shipping Charges",
			"category": "Valuation and Total",
			"add_deduct_tax": "Add",
			"rate": 100
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Net Total",
			"account_head": "_Test Account Customs Duty - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Customs Duty",
			"category": "Valuation",
			"add_deduct_tax": "Add",
			"rate": 10
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Net Total",
			"account_head": "_Test Account Excise Duty - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Excise Duty",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 12
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account Education Cess - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Education Cess",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 2,
			"row_id": 3
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account S&H Education Cess - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "S&H Education Cess",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 1,
			"row_id": 3
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Previous Row Total",
			"account_head": "_Test Account CST - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "CST",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 2,
			"row_id": 5
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Net Total",
			"account_head": "_Test Account VAT - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "VAT",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 12.5
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "On Previous Row Total",
			"account_head": "_Test Account Discount - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Discount",
			"category": "Total",
			"add_deduct_tax": "Deduct",
			"rate": 10,
			"row_id": 7
		},
	],
	[
		# parent
		{
			"doctype": "Purchase Invoice",
			"supplier_name": "_Test Supplier",
			"credit_to": "_Test Supplier - _TC",
			"bill_no": "NA",
			"posting_date": "2013-02-03",
			"fiscal_year": "_Test Fiscal Year 2013",
			"company": "_Test Company",
			"currency": "INR",
			"conversion_rate": 1.0,
			"grand_total_import": 0 # for feed
		},
		# items
		{
			"doctype": "Purchase Invoice Item",
			"parentfield": "entries",
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"qty": 10.0,
			"import_rate": 50.0,
			"uom": "_Test UOM",
			"expense_head": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"conversion_factor": 1.0,
		},
		# taxes
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "Actual",
			"account_head": "_Test Account Shipping Charges - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Shipping Charges",
			"category": "Valuation and Total",
			"add_deduct_tax": "Add",
			"rate": 100.0
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "Actual",
			"account_head": "_Test Account VAT - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "VAT",
			"category": "Total",
			"add_deduct_tax": "Add",
			"rate": 120.0
		},
		{
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "purchase_tax_details",
			"charge_type": "Actual",
			"account_head": "_Test Account Customs Duty - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Customs Duty",
			"category": "Valuation",
			"add_deduct_tax": "Add",
			"rate": 150.0
		},
	]
]