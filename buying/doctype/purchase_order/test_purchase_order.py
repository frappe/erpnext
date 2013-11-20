# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes
import webnotes.defaults
from webnotes.utils import flt

class TestPurchaseOrder(unittest.TestCase):
	def test_make_purchase_receipt(self):		
		from buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		po = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_purchase_receipt, 
			po.doc.name)

		po = webnotes.bean("Purchase Order", po.doc.name)
		po.submit()
		
		pr = make_purchase_receipt(po.doc.name)
		pr[0]["supplier_warehouse"] = "_Test Warehouse 1 - _TC"
		
		self.assertEquals(pr[0]["doctype"], "Purchase Receipt")
		self.assertEquals(len(pr), len(test_records[0]))
		
		pr[0].naming_series = "_T-Purchase Receipt-"
		pr_bean = webnotes.bean(pr)
		pr_bean.insert()
			
	def test_ordered_qty(self):
		webnotes.conn.sql("delete from tabBin")
		
		from buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		po = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_purchase_receipt, 
			po.doc.name)

		po = webnotes.bean("Purchase Order", po.doc.name)
		po.doc.is_subcontracted = "No"
		po.doclist[1].item_code = "_Test Item"
		po.submit()
		
		self.assertEquals(webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse - _TC"}, "ordered_qty"), 10)
		
		pr = make_purchase_receipt(po.doc.name)
		
		self.assertEquals(pr[0]["doctype"], "Purchase Receipt")
		self.assertEquals(len(pr), len(test_records[0]))
		
		pr[0].naming_series = "_T-Purchase Receipt-"
		pr[1].qty = 4.0
		pr_bean = webnotes.bean(pr)
		pr_bean.insert()
		pr_bean.submit()
		
		self.assertEquals(flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse - _TC"}, "ordered_qty")), 6.0)
			
		webnotes.conn.set_value('Item', '_Test Item', 'tolerance', 50)
			
		pr1 = make_purchase_receipt(po.doc.name)
		pr1[0].naming_series = "_T-Purchase Receipt-"
		pr1[1].qty = 8
		pr1_bean = webnotes.bean(pr1)
		pr1_bean.insert()
		pr1_bean.submit()
		
		self.assertEquals(flt(webnotes.conn.get_value("Bin", {"item_code": "_Test Item", 
			"warehouse": "_Test Warehouse - _TC"}, "ordered_qty")), 0.0)
		
	def test_make_purchase_invocie(self):
		from buying.doctype.purchase_order.purchase_order import make_purchase_invoice

		po = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_purchase_invoice, 
			po.doc.name)

		po = webnotes.bean("Purchase Order", po.doc.name)
		po.submit()
		pi = make_purchase_invoice(po.doc.name)
		
		self.assertEquals(pi[0]["doctype"], "Purchase Invoice")
		self.assertEquals(len(pi), len(test_records[0]))

		pi[0].bill_no = "NA"
		webnotes.bean(pi).insert()
		
	def test_subcontracting(self):
		po = webnotes.bean(copy=test_records[0])
		po.insert()
		self.assertEquals(len(po.doclist.get({"parentfield": "po_raw_material_details"})), 2)

	def test_warehouse_company_validation(self):
		from stock.utils import InvalidWarehouseCompany
		po = webnotes.bean(copy=test_records[0])
		po.doc.company = "_Test Company 1"
		po.doc.conversion_rate = 0.0167
		self.assertRaises(InvalidWarehouseCompany, po.insert)

	def test_uom_integer_validation(self):
		from utilities.transaction_base import UOMMustBeIntegerError
		po = webnotes.bean(copy=test_records[0])
		po.doclist[1].qty = 3.4
		self.assertRaises(UOMMustBeIntegerError, po.insert)


test_dependencies = ["BOM"]

test_records = [
	[
		{
			"company": "_Test Company", 
			"naming_series": "_T-Purchase Order-",
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"doctype": "Purchase Order", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"transaction_date": "2013-02-12", 
			"is_subcontracted": "Yes",
			"supplier": "_Test Supplier",
			"supplier_name": "_Test Supplier",
			"net_total": 5000.0, 
			"grand_total": 5000.0,
			"grand_total_import": 5000.0,
		}, 
		{
			"conversion_factor": 1.0, 
			"description": "_Test FG Item", 
			"doctype": "Purchase Order Item", 
			"item_code": "_Test FG Item", 
			"item_name": "_Test FG Item", 
			"parentfield": "po_details", 
			"qty": 10.0,
			"import_rate": 500.0,
			"amount": 5000.0,
			"warehouse": "_Test Warehouse - _TC", 
			"stock_uom": "_Test UOM", 
			"uom": "_Test UOM",
			"schedule_date": "2013-03-01"
		}
	],
]