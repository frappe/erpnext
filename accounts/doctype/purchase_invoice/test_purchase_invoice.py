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
from webnotes.utils import nowdate

from stock.doctype.purchase_receipt import test_purchase_receipt

company = webnotes.conn.get_default("company")
abbr = webnotes.conn.get_value("Company", company, "abbr")

def load_data():
	test_purchase_receipt.load_data()
	
	webnotes.insert({"doctype": "Account", "account_name": "Cost for Goods Sold",
		"parent_account": "Expenses - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "Excise Duty",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "Education Cess",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
	
	webnotes.insert({"doctype": "Account", "account_name": "S&H Education Cess",
		"parent_account": "Tax Assets - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	webnotes.insert({"doctype": "Account", "account_name": "CST",
		"parent_account": "Direct Expenses - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	webnotes.insert({"doctype": "Account", "account_name": "Discount",
		"parent_account": "Direct Expenses - %s" % abbr, "company": company,
		"group_or_ledger": "Ledger"})
		
	from webnotes.model.doc import Document
	item = Document("Item", "Home Desktop 100")
	
	# excise duty
	item_tax = item.addchild("item_tax", "Item Tax")
	item_tax.tax_type = "Excise Duty - %s" % abbr
	item_tax.tax_rate = 10
	item_tax.save()

import json	
purchase_invoice_doclist = [
	# parent
	{
		"doctype": "Purchase Invoice", 
		"credit_to": "East Wind Inc. - %s" % abbr,
		"supplier_name": "East Wind Inc.",
		"naming_series": "BILL", "posting_date": nowdate(),
		"company": company, "fiscal_year": webnotes.conn.get_default("fiscal_year"), 
		"currency": webnotes.conn.get_default("currency"), "conversion_rate": 1,
		'net_total': 1250.00, 'grand_total': 1512.30, 'grand_total_import': 1512.30, 
	},
	# items
	{
		"doctype": "Purchase Invoice Item", 
		"item_code": "Home Desktop 100", "qty": 10, "import_rate": 50, "rate": 50,
		"amount": 500, "import_amount": 500, "parentfield": "entries", 
		"uom": "Nos", "item_tax_rate": json.dumps({"Excise Duty - %s" % abbr: 10}),
		"expense_head": "Cost for Goods Sold - %s" % abbr, 
		"cost_center": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Purchase Invoice Item", 
		"item_code": "Home Desktop 200", "qty": 5, "import_rate": 150, "rate": 150, 
		"amount": 750, "import_amount": 750, "parentfield": "entries", "uom": "Nos", 
		"expense_head": "Cost for Goods Sold - %s" % abbr, 
		"cost_center": "Default Cost Center - %s" % abbr
	},
	# taxes
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "Actual",
		"account_head": "Shipping Charges - %s" % abbr, "rate": 100, "tax_amount": 100, 
		"category": "Valuation and Total", "parentfield": "other_charges",
		"cost_center": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "Customs Duty - %s" % abbr, "rate": 10, "tax_amount": 125.00,
		"category": "Valuation", "parentfield": "other_charges",
		"cost_center": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "Excise Duty - %s" % abbr, "rate": 12, "tax_amount": 140.00, 
		"category": "Total", "parentfield": "other_charges"
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Previous Row Amount",
		"account_head": "Education Cess - %s" % abbr, "rate": 2, "row_id": 3, "tax_amount": 2.80,
		"category": "Total", "parentfield": "other_charges"
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Previous Row Amount",
		"account_head": "S&H Education Cess - %s" % abbr, "rate": 1, "row_id": 3, 
		"tax_amount": 1.4, "category": "Total", "parentfield": "other_charges"
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Previous Row Total",
		"account_head": "CST - %s" % abbr, "rate": 2, "row_id": 5, "tax_amount": 29.88, 
		"category": "Total", "parentfield": "other_charges",
		"cost_center": "Default Cost Center - %s" % abbr
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Net Total",
		"account_head": "VAT - Test - %s" % abbr, "rate": 12.5, "tax_amount": 156.25, 
		"category": "Total", "parentfield": "other_charges"
	},
	{
		"doctype": "Purchase Taxes and Charges", "charge_type": "On Previous Row Total",
		"account_head": "Discount - %s" % abbr, "rate": -10, "row_id": 7, "tax_amount": -168.03, 
		"category": "Total", "parentfield": "other_charges",
		"cost_center": "Default Cost Center - %s" % abbr
	},
]

class TestPurchaseReceipt(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		load_data()
		# webnotes.conn.set_value("Global Defaults", None, "automatic_inventory_accounting", 1)
			
	def test_gl_entries(self):
		from webnotes.model.doclist import DocList
		controller = webnotes.insert(DocList(purchase_invoice_doclist))
		controller.submit()
		controller.load_from_db()
		dl = controller.doclist
		
		expected_gl_entries = {
			"East Wind Inc. - %s" % abbr : [0, 1512.30],
			"Cost for Goods Sold - %s" % abbr : [1250, 0],
			"Shipping Charges - %s" % abbr : [100, 0],
			"Excise Duty - %s" % abbr : [140, 0],
			"Education Cess - %s" % abbr : [2.8, 0],
			"S&H Education Cess - %s" % abbr : [1.4, 0],
			"CST - %s" % abbr : [29.88, 0],
			"VAT - Test - %s" % abbr : [156.25, 0],
			"Discount - %s" % abbr : [0, 168.03],
		}
		gl_entries = webnotes.conn.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type = 'Purchase Invoice' and voucher_no = %s""", dl[0].name, as_dict=1)
		for d in gl_entries:
			self.assertEqual([d.debit, d.credit], expected_gl_entries.get(d.account))

	def tearDown(self):
		webnotes.conn.rollback()