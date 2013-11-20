# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.defaults

class TestPurchaseOrder(unittest.TestCase):
	def test_make_purchase_order(self):
		from buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

		sq = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_purchase_order, 
			sq.doc.name)

		sq = webnotes.bean("Supplier Quotation", sq.doc.name)
		sq.submit()
		po = make_purchase_order(sq.doc.name)
		
		self.assertEquals(po[0]["doctype"], "Purchase Order")
		self.assertEquals(len(po), len(sq.doclist))
		
		po[0]["naming_series"] = "_T-Purchase Order-"

		for doc in po:
			if doc.get("item_code"):
				doc["schedule_date"] = "2013-04-12"

		webnotes.bean(po).insert()
		
test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"doctype": "Supplier Quotation", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"transaction_date": "2013-02-12", 
			"is_subcontracted": "No",
			"supplier": "_Test Supplier",
			"supplier_name": "_Test Supplier",
			"net_total": 5000.0, 
			"grand_total": 5000.0,
			"grand_total_import": 5000.0,
			"naming_series": "_T-Supplier Quotation-"
		}, 
		{
			"description": "_Test FG Item", 
			"doctype": "Supplier Quotation Item", 
			"item_code": "_Test FG Item", 
			"item_name": "_Test FG Item", 
			"parentfield": "quotation_items", 
			"qty": 10.0,
			"import_rate": 500.0,
			"amount": 5000.0,
			"warehouse": "_Test Warehouse - _TC", 
			"uom": "_Test UOM",
		}
	],
]