# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import flt
import unittest

class TestSalesOrder(unittest.TestCase):
	def test_make_material_request(self):
		from selling.doctype.sales_order.sales_order import make_material_request
		
		so = webnotes.bean(copy=test_records[0]).insert()
		
		self.assertRaises(webnotes.ValidationError, make_material_request, 
			so.doc.name)

		sales_order = webnotes.bean("Sales Order", so.doc.name)
		sales_order.submit()
		mr = make_material_request(so.doc.name)
		
		self.assertEquals(mr[0]["material_request_type"], "Purchase")
		self.assertEquals(len(mr), len(sales_order.doclist))

	def test_make_delivery_note(self):
		from selling.doctype.sales_order.sales_order import make_delivery_note

		so = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_delivery_note, 
			so.doc.name)

		sales_order = webnotes.bean("Sales Order", so.doc.name)
		sales_order.submit()
		dn = make_delivery_note(so.doc.name)
		
		self.assertEquals(dn[0]["doctype"], "Delivery Note")
		self.assertEquals(len(dn), len(sales_order.doclist))

	def test_make_sales_invoice(self):
		from selling.doctype.sales_order.sales_order import make_sales_invoice

		so = webnotes.bean(copy=test_records[0]).insert()

		self.assertRaises(webnotes.ValidationError, make_sales_invoice, 
			so.doc.name)

		sales_order = webnotes.bean("Sales Order", so.doc.name)
		sales_order.submit()
		si = make_sales_invoice(so.doc.name)
		
		self.assertEquals(si[0]["doctype"], "Sales Invoice")
		self.assertEquals(len(si), len(sales_order.doclist))
		self.assertEquals(len([d for d in si if d["doctype"]=="Sales Invoice Item"]), 1)
		
		si = webnotes.bean(si)
		si.insert()
		si.submit()

		si1 = make_sales_invoice(so.doc.name)
		self.assertEquals(len([d for d in si1 if d["doctype"]=="Sales Invoice Item"]), 0)
		

	def create_so(self, so_doclist = None):
		if not so_doclist:
			so_doclist = test_records[0]
		
		w = webnotes.bean(copy=so_doclist)
		w.insert()
		w.submit()

		return w
		
	def create_dn_against_so(self, so, delivered_qty=0):
		from stock.doctype.delivery_note.test_delivery_note import test_records as dn_test_records
		from stock.doctype.delivery_note.test_delivery_note import _insert_purchase_receipt

		_insert_purchase_receipt(so.doclist[1].item_code)
		
		dn = webnotes.bean(webnotes.copy_doclist(dn_test_records[0]))
		dn.doclist[1].item_code = so.doclist[1].item_code
		dn.doclist[1].against_sales_order = so.doc.name
		dn.doclist[1].prevdoc_detail_docname = so.doclist[1].name
		if delivered_qty:
			dn.doclist[1].qty = delivered_qty
		dn.insert()
		dn.submit()
		return dn
		
	def get_bin_reserved_qty(self, item_code, warehouse):
		return flt(webnotes.conn.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, 
			"reserved_qty"))
	
	def delete_bin(self, item_code, warehouse):
		bin = webnotes.conn.exists({"doctype": "Bin", "item_code": item_code, 
			"warehouse": warehouse})
		if bin:
			webnotes.delete_doc("Bin", bin[0][0])
			
	def check_reserved_qty(self, item_code, warehouse, qty):
		bin_reserved_qty = self.get_bin_reserved_qty(item_code, warehouse)
		self.assertEqual(bin_reserved_qty, qty)
		
	def test_reserved_qty_for_so(self):
		# reset bin
		self.delete_bin(test_records[0][1]["item_code"], test_records[0][1]["reserved_warehouse"])
		
		# submit
		so = self.create_so()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 10.0)
		
		# cancel
		so.cancel()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 0.0)
		
	
	def test_reserved_qty_for_partial_delivery(self):
		# reset bin
		self.delete_bin(test_records[0][1]["item_code"], test_records[0][1]["reserved_warehouse"])
		
		# submit so
		so = self.create_so()
		
		# allow negative stock
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		# submit dn
		dn = self.create_dn_against_so(so)
		
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 5.0)
		
		# stop so
		so.load_from_db()
		so.obj.stop_sales_order()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 0.0)
		
		# unstop so
		so.load_from_db()
		so.obj.unstop_sales_order()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 5.0)
		
		# cancel dn
		dn.cancel()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 10.0)
		
	def test_reserved_qty_for_over_delivery(self):
		# reset bin
		self.delete_bin(test_records[0][1]["item_code"], test_records[0][1]["reserved_warehouse"])
		
		# submit so
		so = self.create_so()
		
		# allow negative stock
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		# set over-delivery tolerance
		webnotes.conn.set_value('Item', so.doclist[1].item_code, 'tolerance', 50)
		
		# submit dn
		dn = self.create_dn_against_so(so, 15)
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 0.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(so.doclist[1].item_code, so.doclist[1].reserved_warehouse, 10.0)
		
	def test_reserved_qty_for_so_with_packing_list(self):
		from selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records
		
		# change item in test so record
		test_record = test_records[0][:]
		test_record[1]["item_code"] = "_Test Sales BOM Item"
		
		# reset bin
		self.delete_bin(sbom_test_records[0][1]["item_code"], test_record[1]["reserved_warehouse"])
		self.delete_bin(sbom_test_records[0][2]["item_code"], test_record[1]["reserved_warehouse"])
		
		# submit
		so = self.create_so(test_record)
		
		
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 20.0)
		
		# cancel
		so.cancel()
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)
			
	def test_reserved_qty_for_partial_delivery_with_packing_list(self):
		from selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records
		
		# change item in test so record
		
		test_record = webnotes.copy_doclist(test_records[0])
		test_record[1]["item_code"] = "_Test Sales BOM Item"

		# reset bin
		self.delete_bin(sbom_test_records[0][1]["item_code"], test_record[1]["reserved_warehouse"])
		self.delete_bin(sbom_test_records[0][2]["item_code"], test_record[1]["reserved_warehouse"])
		
		# submit
		so = self.create_so(test_record)
		
		# allow negative stock
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		# submit dn
		dn = self.create_dn_against_so(so)
		
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 25.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 10.0)
				
		# stop so
		so.load_from_db()
		so.obj.stop_sales_order()
		
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)
		
		# unstop so
		so.load_from_db()
		so.obj.unstop_sales_order()
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 25.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 10.0)
		
		# cancel dn
		dn.cancel()
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 20.0)
			
	def test_reserved_qty_for_over_delivery_with_packing_list(self):
		from selling.doctype.sales_bom.test_sales_bom import test_records as sbom_test_records
		
		# change item in test so record
		test_record = webnotes.copy_doclist(test_records[0])
		test_record[1]["item_code"] = "_Test Sales BOM Item"

		# reset bin
		self.delete_bin(sbom_test_records[0][1]["item_code"], test_record[1]["reserved_warehouse"])
		self.delete_bin(sbom_test_records[0][2]["item_code"], test_record[1]["reserved_warehouse"])
		
		# submit
		so = self.create_so(test_record)
		
		# allow negative stock
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		# set over-delivery tolerance
		webnotes.conn.set_value('Item', so.doclist[1].item_code, 'tolerance', 50)
		
		# submit dn
		dn = self.create_dn_against_so(so, 15)
		
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 0.0)

		# cancel dn
		dn.cancel()
		self.check_reserved_qty(sbom_test_records[0][1]["item_code"], 
			so.doclist[1].reserved_warehouse, 50.0)
		self.check_reserved_qty(sbom_test_records[0][2]["item_code"], 
			so.doclist[1].reserved_warehouse, 20.0)

	def test_warehouse_user(self):
		webnotes.bean("Profile", "test@example.com").get_controller()\
			.add_roles("Sales User", "Sales Manager", "Material User", "Material Manager")
			
		webnotes.bean("Profile", "test2@example.com").get_controller()\
			.add_roles("Sales User", "Sales Manager", "Material User", "Material Manager")
		
		webnotes.session.user = "test@example.com"

		from stock.utils import UserNotAllowedForWarehouse
		so = webnotes.bean(copy = test_records[0])
		so.doc.company = "_Test Company 1"
		so.doc.conversion_rate = 0.02
		so.doc.plc_conversion_rate = 0.02
		so.doclist[1].reserved_warehouse = "_Test Warehouse 2 - _TC1"
		self.assertRaises(UserNotAllowedForWarehouse, so.insert)

		webnotes.session.user = "test2@example.com"
		so.insert()

		webnotes.session.user = "Administrator"

test_dependencies = ["Sales BOM"]
	
test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"customer": "_Test Customer", 
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group", 
			"doctype": "Sales Order", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"order_type": "Sales",
			"delivery_date": "2013-02-23",
			"plc_conversion_rate": 1.0, 
			"price_list_currency": "INR", 
			"selling_price_list": "_Test Price List", 
			"territory": "_Test Territory", 
			"transaction_date": "2013-02-21",
			"grand_total": 1000.0, 
			"grand_total_export": 1000.0, 
			"naming_series": "_T-Sales Order-"
		}, 
		{
			"description": "CPU", 
			"doctype": "Sales Order Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"item_name": "CPU", 
			"parentfield": "sales_order_details", 
			"qty": 10.0,
			"basic_rate": 100.0,
			"export_rate": 100.0,
			"amount": 1000.0,
			"reserved_warehouse": "_Test Warehouse - _TC",
		}
	],	
]