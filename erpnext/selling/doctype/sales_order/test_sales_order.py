# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
from frappe.utils import flt, add_days
import frappe.permissions
import unittest
from erpnext.selling.doctype.sales_order.sales_order \
	import make_material_request, make_delivery_note, make_sales_invoice, WarehouseRequired
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.tests.test_permissions import set_user_permission_doctypes
from erpnext.selling.doctype.sales_order.sales_order import make_production_orders
import json


class TestSalesOrder(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

		for role in ("Stock User", "Sales User"):
			set_user_permission_doctypes(doctypes="Sales Order", role=role,
				apply_user_permissions=0, user_permission_doctypes=None)

	def test_make_material_request(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_material_request, so.name)

		so.submit()
		mr = make_material_request(so.name)

		self.assertEquals(mr.material_request_type, "Purchase")
		self.assertEquals(len(mr.get("items")), len(so.get("items")))

	def test_make_delivery_note(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_delivery_note, so.name)

		so.submit()
		dn = make_delivery_note(so.name)

		self.assertEquals(dn.doctype, "Delivery Note")
		self.assertEquals(len(dn.get("items")), len(so.get("items")))

	def test_make_sales_invoice(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEquals(len(si.get("items")), len(so.get("items")))
		self.assertEquals(len(si.get("items")), 1)

		si.insert()
		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEquals(len(si1.get("items")), 0)

	def test_make_sales_invoice_with_terms(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.update({"payment_terms_template": "_Test Payment Term Template"})

		so.save()
		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEquals(len(si.get("items")), len(so.get("items")))
		self.assertEquals(len(si.get("items")), 1)

		si.insert()

		self.assertEqual(si.payment_schedule[0].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[0].due_date, so.transaction_date)
		self.assertEqual(si.payment_schedule[1].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[1].due_date, add_days(so.transaction_date, 30))

		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEquals(len(si1.get("items")), 0)

	def test_update_qty(self):
		so = make_sales_order()

		create_dn_against_so(so.name, 6)

		so.load_from_db()
		self.assertEquals(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice without update_stock checked
		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 6
		si1.insert()
		si1.submit()

		so.load_from_db()
		self.assertEquals(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice with update_stock checked
		si2 = make_sales_invoice(so.name)
		si2.set("update_stock", 1)
		si2.get("items")[0].qty = 3
		si2.insert()
		si2.submit()

		so.load_from_db()
		self.assertEquals(so.get("items")[0].delivered_qty, 9)

	def test_reserved_qty_for_partial_delivery(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		dn = create_dn_against_so(so.name)
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 5)

		# close so
		so.load_from_db()
		so.update_status("Closed")
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		# unclose so
		so.load_from_db()
		so.update_status('Draft')
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 5)

		dn.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		# cancel
		so.load_from_db()
		so.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

	def test_reserved_qty_for_over_delivery(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		# set over-delivery tolerance
		frappe.db.set_value('Item', "_Test Item", 'tolerance', 50)

		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		dn = create_dn_against_so(so.name, 15)
		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		dn.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

	def test_reserved_qty_for_over_delivery_via_sales_invoice(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)

		# set over-delivery tolerance
		frappe.db.set_value('Item', "_Test Item", 'tolerance', 50)

		existing_reserved_qty = get_reserved_qty()

		so = make_sales_order()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.get("items")[0].qty = 12
		si.insert()
		si.submit()

		self.assertEqual(get_reserved_qty(), existing_reserved_qty)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 12)
		self.assertEqual(so.per_delivered, 100)

		si.cancel()
		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 10)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 0)
		self.assertEqual(so.per_delivered, 0)

	def test_reserved_qty_for_partial_delivery_with_packing_list(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		make_stock_entry(item="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, rate=100)

		existing_reserved_qty_item1 = get_reserved_qty("_Test Item")
		existing_reserved_qty_item2 = get_reserved_qty("_Test Item Home Desktop 100")

		so = make_sales_order(item_code="_Test Product Bundle Item")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 10)

		# close so
		so.load_from_db()
		so.update_status("Closed")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

		# unclose so
		so.load_from_db()
		so.update_status('Draft')

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 25)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 10)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		so.load_from_db()
		so.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"), existing_reserved_qty_item2)

	def test_reserved_qty_for_over_delivery_with_packing_list(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		make_stock_entry(item="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=10, rate=100)

		# set over-delivery tolerance
		frappe.db.set_value('Item', "_Test Product Bundle Item", 'tolerance', 50)

		existing_reserved_qty_item1 = get_reserved_qty("_Test Item")
		existing_reserved_qty_item2 = get_reserved_qty("_Test Item Home Desktop 100")

		so = make_sales_order(item_code="_Test Product Bundle Item")

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

		dn = create_dn_against_so(so.name, 15)

		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2)

		dn.cancel()
		self.assertEqual(get_reserved_qty("_Test Item"), existing_reserved_qty_item1 + 50)
		self.assertEqual(get_reserved_qty("_Test Item Home Desktop 100"),
			existing_reserved_qty_item2 + 20)

	def test_warehouse_user(self):
		for role in ("Stock User", "Sales User"):
			set_user_permission_doctypes(doctypes="Sales Order", role=role,
				apply_user_permissions=1, user_permission_doctypes=["Warehouse"])

		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		frappe.permissions.add_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		frappe.permissions.add_user_permission("Company", "_Test Company 1", "test2@example.com")

		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Sales User", "Stock User")
		test_user.remove_roles("Sales Manager")

		test_user_2 = frappe.get_doc("User", "test2@example.com")
		test_user_2.add_roles("Sales User", "Stock User")
		test_user_2.remove_roles("Sales Manager")

		frappe.set_user("test@example.com")

		so = make_sales_order(company="_Test Company 1",
			warehouse="_Test Warehouse 2 - _TC1", do_not_save=True)
		so.conversion_rate = 0.02
		so.plc_conversion_rate = 0.02
		self.assertRaises(frappe.PermissionError, so.insert)

		frappe.set_user("test2@example.com")
		so.insert()

		frappe.set_user("Administrator")
		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 1 - _TC", "test@example.com")
		frappe.permissions.remove_user_permission("Warehouse", "_Test Warehouse 2 - _TC1", "test2@example.com")
		frappe.permissions.remove_user_permission("Company", "_Test Company 1", "test2@example.com")

	def test_block_delivery_note_against_cancelled_sales_order(self):
		so = make_sales_order()

		dn = make_delivery_note(so.name)
		dn.insert()

		so.cancel()

		self.assertRaises(frappe.CancelledLinkError, dn.submit)

	def test_service_type_product_bundle(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		make_item("_Test Service Product Bundle", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 1", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle("_Test Service Product Bundle",
			["_Test Service Product Bundle Item 1", "_Test Service Product Bundle Item 2"])

		so = make_sales_order(item_code = "_Test Service Product Bundle", warehouse=None)

		self.assertTrue("_Test Service Product Bundle Item 1" in [d.item_code for d in so.packed_items])
		self.assertTrue("_Test Service Product Bundle Item 2" in [d.item_code for d in so.packed_items])

	def test_mix_type_product_bundle(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		make_item("_Test Mix Product Bundle", {"is_stock_item": 0})
		make_item("_Test Mix Product Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Mix Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle("_Test Mix Product Bundle",
			["_Test Mix Product Bundle Item 1", "_Test Mix Product Bundle Item 2"])

		self.assertRaises(WarehouseRequired, make_sales_order, item_code = "_Test Mix Product Bundle", warehouse="")

	def test_auto_insert_price(self):
		from erpnext.stock.doctype.item.test_item import make_item
		make_item("_Test Item for Auto Price List", {"is_stock_item": 0})
		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 1)

		item_price = frappe.db.get_value("Item Price", {"price_list": "_Test Price List",
			"item_code": "_Test Item for Auto Price List"})
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(item_code = "_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100)

		self.assertEquals(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), 100)


		# do not update price list
		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 0)

		item_price = frappe.db.get_value("Item Price", {"price_list": "_Test Price List",
			"item_code": "_Test Item for Auto Price List"})
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(item_code = "_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100)

		self.assertEquals(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), None)

		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 1)

	def test_drop_shipping(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_drop_shipment
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status

		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)

		po_item = make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1,
        'default_supplier': '_Test Supplier',
		    "expense_account": "_Test Account Cost for Goods Sold - _TC",
		    "cost_center": "_Test Cost Center - _TC"
			})

		dn_item = make_item("_Test Regular Item", {"is_stock_item": 1, "expense_account": "_Test Account Cost for Goods Sold - _TC",
  		  	"cost_center": "_Test Cost Center - _TC"})

		so_items = [
			{
				"item_code": po_item.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": '_Test Supplier'
			},
			{
				"item_code": dn_item.item_code,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 2,
				"rate": 300,
				"conversion_factor": 1.0
			}
		]

		if frappe.db.get_value("Item", "_Test Regular Item", "is_stock_item")==1:
			make_stock_entry(item="_Test Regular Item", target="_Test Warehouse - _TC", qty=10, rate=100)

		#setuo existing qty from bin
		bin = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

		existing_ordered_qty = bin[0].ordered_qty if bin else 0.0
		existing_reserved_qty = bin[0].reserved_qty if bin else 0.0

		bin = frappe.get_all("Bin", filters={"item_code": dn_item.item_code,
			"warehouse": "_Test Warehouse - _TC"}, fields=["reserved_qty"])

		existing_reserved_qty_for_dn_item = bin[0].reserved_qty if bin else 0.0

		#create so, po and partial dn
		so = make_sales_order(item_list=so_items, do_not_submit=True)
		so.submit()

		po = make_purchase_order_for_drop_shipment(so.name, '_Test Supplier')
		po.submit()

		dn = create_dn_against_so(so.name, delivered_qty=1)

		self.assertEquals(so.customer, po.customer)
		self.assertEquals(po.items[0].sales_order, so.name)
		self.assertEquals(po.items[0].item_code, po_item.item_code)
		self.assertEquals(dn.items[0].item_code, dn_item.item_code)

		#test ordered_qty and reserved_qty
		bin = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

		ordered_qty = bin[0].ordered_qty if bin else 0.0
		reserved_qty = bin[0].reserved_qty if bin else 0.0

		self.assertEquals(abs(flt(ordered_qty)), existing_ordered_qty)
		self.assertEquals(abs(flt(reserved_qty)), existing_reserved_qty)

		reserved_qty = frappe.db.get_value("Bin",
					{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEquals(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item + 1)

		#test po_item length
		self.assertEquals(len(po.items), 1)

		#test per_delivered status
		update_status("Delivered", po.name)
		self.assertEquals(flt(frappe.db.get_value("Sales Order", so.name, "per_delivered"), 2), 75.00)

		#test reserved qty after complete delivery
		dn = create_dn_against_so(so.name, delivered_qty=1)
		reserved_qty = frappe.db.get_value("Bin",
			{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEquals(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item)

		#test after closing so
		so.db_set('status', "Closed")
		so.update_reserved_qty()

		bin = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

		ordered_qty = bin[0].ordered_qty if bin else 0.0
		reserved_qty = bin[0].reserved_qty if bin else 0.0

		self.assertEquals(abs(flt(ordered_qty)), existing_ordered_qty)
		self.assertEquals(abs(flt(reserved_qty)), existing_reserved_qty)

		reserved_qty = frappe.db.get_value("Bin",
			{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEquals(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item)

	def test_reserved_qty_for_closing_so(self):
		bin = frappe.get_all("Bin", filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["reserved_qty"])

		existing_reserved_qty = bin[0].reserved_qty if bin else 0.0

		so = make_sales_order(item_code="_Test Item", qty=1)

		self.assertEquals(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty+1)

		so.update_status("Closed")

		self.assertEquals(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty)

	def test_create_so_with_margin(self):
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		so.items[0].price_list_rate = price_list_rate = 100
		so.items[0].margin_type = 'Percentage'
		so.items[0].margin_rate_or_amount = 25
		so.save()

		new_so = frappe.copy_doc(so)
		new_so.save(ignore_permissions=True)

		self.assertEquals(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))
		new_so.items[0].margin_rate_or_amount = 25
		new_so.payment_schedule = []
		new_so.save()
		new_so.submit()

		self.assertEquals(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))

	def test_terms_auto_added(self):
		so = make_sales_order(do_not_save=1)

		self.assertFalse(so.get('payment_schedule'))

		so.insert()

		self.assertTrue(so.get('payment_schedule'))

	def test_terms_not_copied(self):
		so = make_sales_order()
		self.assertTrue(so.get('payment_schedule'))

		si = make_sales_invoice(so.name)
		self.assertFalse(si.get('payment_schedule'))

	def test_terms_copied(self):
		so = make_sales_order(do_not_copy=1, do_not_save=1)
		so.payment_terms_template = '_Test Payment Term Template'
		so.insert()
		so.submit()
		self.assertTrue(so.get('payment_schedule'))

		si = make_sales_invoice(so.name)
		si.insert()
		self.assertTrue(si.get('payment_schedule'))

	def test_make_production_order(self):
		# Make a new Sales Order
		so = make_sales_order(**{
			"item_list": [{
				"item_code": "_Test FG Item",
				"qty": 10,
				"rate":100
			},
			{
				"item_code": "_Test FG Item",
				"qty": 20,
				"rate":200
			}]
		})

		# Raise Production Orders
		po_items= []
		so_item_name= {}
		for item in so.get_production_order_items():
			po_items.append({
				"warehouse": item.get("warehouse"),
				"item_code": item.get("item_code"),
				"pending_qty": item.get("pending_qty"),
				"sales_order_item": item.get("sales_order_item"),
				"bom": item.get("bom")
			})
			so_item_name[item.get("sales_order_item")]= item.get("pending_qty")
		make_production_orders(json.dumps({"items":po_items}), so.name, so.company)

		# Check if Production Orders were raised
		for item in so_item_name:
			po_qty = frappe.db.sql("select sum(qty) from `tabProduction Order` where sales_order=%s and sales_order_item=%s", (so.name, item))
			self.assertEquals(po_qty[0][0], so_item_name.get(item))

def make_sales_order(**args):
	so = frappe.new_doc("Sales Order")
	args = frappe._dict(args)
	if args.transaction_date:
		so.transaction_date = args.transaction_date

	so.company = args.company or "_Test Company"
	so.customer = args.customer or "_Test Customer"
	so.currency = args.currency or "INR"
	if args.selling_price_list:
		so.selling_price_list = args.selling_price_list

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			so.append("items", item)

	else:
		so.append("items", {
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse,
			"qty": args.qty or 10,
			"uom": args.uom or None,
			"rate": args.rate or 100
		})

	so.delivery_date = add_days(so.transaction_date, 10)

	if not args.do_not_save:
		so.insert()
		if not args.do_not_submit:
			so.submit()
		else:
			so.payment_schedule = []
	else:
		so.payment_schedule = []

	return so

def create_dn_against_so(so, delivered_qty=0):
	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	dn = make_delivery_note(so)
	dn.get("items")[0].qty = delivered_qty or 5
	dn.insert()
	dn.submit()
	return dn

def get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
		"reserved_qty"))

test_dependencies = ["Currency Exchange"]
