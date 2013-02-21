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

test_dependencies = ["Item", "Cost Center"]

class TestPurchaseInvoice(unittest.TestCase):
	def test_gl_entries(self):
		wrapper = webnotes.bean(self.get_test_doclist())
		
		# circumvent the disabled calculation call
		obj = webnotes.get_obj(doc=wrapper.doc, doclist=wrapper.doclist)
		obj.calculate_taxes_and_totals()
		wrapper.set_doclist(obj.doclist)
		
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
			
	def test_purchase_invoice_calculation(self):
		wrapper = webnotes.bean(self.get_test_doclist())
		
		# circumvent the disabled calculation call
		obj = webnotes.get_obj(doc=wrapper.doc, doclist=wrapper.doclist)
		obj.calculate_taxes_and_totals()
		wrapper.set_doclist(obj.doclist)

		wrapper.insert()
		wrapper.load_from_db()
		
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
			# print tax.account_head, tax.tax_amount, tax.item_wise_tax_detail

		expected_values = [
			["_Test Item Home Desktop 100", 90],
			["_Test Item Home Desktop 200", 135]
		]
		for i, item in enumerate(wrapper.doclist.get({"parentfield": "entries"})):
			self.assertEqual(item.item_code, expected_values[i][0])
			self.assertEqual(item.item_tax_amount, expected_values[i][1])
			
	def get_test_doclist(self):
		return [
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
				"cost_center": "_Test Cost Center - _TC"
				
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
				"cost_center": "_Test Cost Center - _TC"
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
		]