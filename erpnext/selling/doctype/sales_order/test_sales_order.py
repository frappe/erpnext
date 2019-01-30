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
from erpnext.selling.doctype.sales_order.sales_order import make_work_orders
from erpnext.controllers.accounts_controller import update_child_qty_rate
import json
from erpnext.selling.doctype.sales_order.sales_order import make_raw_material_request
class TestSalesOrder(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_make_material_request(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_material_request, so.name)

		so.submit()
		mr = make_material_request(so.name)

		self.assertEqual(mr.material_request_type, "Purchase")
		self.assertEqual(len(mr.get("items")), len(so.get("items")))

	def test_make_delivery_note(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_delivery_note, so.name)

		so.submit()
		dn = make_delivery_note(so.name)

		self.assertEqual(dn.doctype, "Delivery Note")
		self.assertEqual(len(dn.get("items")), len(so.get("items")))

	def test_make_sales_invoice(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEqual(len(si.get("items")), len(so.get("items")))
		self.assertEqual(len(si.get("items")), 1)

		si.insert()
		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEqual(len(si1.get("items")), 0)

	def test_so_billed_amount_against_return_entry(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
		so = make_sales_order(do_not_submit=True)
		so.submit()

		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()

		si1 = make_sales_return(si.name)
		si1.update_billed_amount_in_sales_order = 1
		si1.submit()
		so.load_from_db()
		self.assertEquals(so.per_billed, 0)

	def test_make_sales_invoice_with_terms(self):
		so = make_sales_order(do_not_submit=True)

		self.assertRaises(frappe.ValidationError, make_sales_invoice, so.name)

		so.update({"payment_terms_template": "_Test Payment Term Template"})

		so.save()
		so.submit()
		si = make_sales_invoice(so.name)

		self.assertEqual(len(si.get("items")), len(so.get("items")))
		self.assertEqual(len(si.get("items")), 1)

		si.insert()

		self.assertEqual(si.payment_schedule[0].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[0].due_date, so.transaction_date)
		self.assertEqual(si.payment_schedule[1].payment_amount, 500.0)
		self.assertEqual(si.payment_schedule[1].due_date, add_days(so.transaction_date, 30))

		si.submit()

		si1 = make_sales_invoice(so.name)
		self.assertEqual(len(si1.get("items")), 0)

	def test_update_qty(self):
		so = make_sales_order()

		create_dn_against_so(so.name, 6)

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice without update_stock checked
		si1 = make_sales_invoice(so.name)
		si1.get("items")[0].qty = 6
		si1.insert()
		si1.submit()

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 6)

		# Check delivered_qty after make_sales_invoice with update_stock checked
		si2 = make_sales_invoice(so.name)
		si2.set("update_stock", 1)
		si2.get("items")[0].qty = 3
		si2.insert()
		si2.submit()

		so.load_from_db()
		self.assertEqual(so.get("items")[0].delivered_qty, 9)

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

	def test_update_child_qty_rate(self):
		so = make_sales_order(item_code= "_Test Item", qty=4)
		create_dn_against_so(so.name, 4)
		make_sales_invoice(so.name)

		existing_reserved_qty = get_reserved_qty()

		trans_item = json.dumps([{'item_code' : '_Test Item', 'rate' : 200, 'qty' : 7, 'docname': so.items[0].name}])
		update_child_qty_rate('Sales Order', trans_item, so.name)

		so.reload()
		self.assertEqual(so.get("items")[0].rate, 200)
		self.assertEqual(so.get("items")[0].qty, 7)
		self.assertEqual(so.get("items")[0].amount, 1400)
		self.assertEqual(so.status, 'To Deliver and Bill')

		self.assertEqual(get_reserved_qty(), existing_reserved_qty + 3)

	def test_warehouse_user(self):
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
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item
		make_item("_Test Service Product Bundle", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 1", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 2", {"is_stock_item": 0})

		make_product_bundle("_Test Service Product Bundle",
			["_Test Service Product Bundle Item 1", "_Test Service Product Bundle Item 2"])

		so = make_sales_order(item_code = "_Test Service Product Bundle", warehouse=None)

		self.assertTrue("_Test Service Product Bundle Item 1" in [d.item_code for d in so.packed_items])
		self.assertTrue("_Test Service Product Bundle Item 2" in [d.item_code for d in so.packed_items])

	def test_mix_type_product_bundle(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item
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

		self.assertEqual(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), 100)


		# do not update price list
		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 0)

		item_price = frappe.db.get_value("Item Price", {"price_list": "_Test Price List",
			"item_code": "_Test Item for Auto Price List"})
		if item_price:
			frappe.delete_doc("Item Price", item_price)

		make_sales_order(item_code = "_Test Item for Auto Price List", selling_price_list="_Test Price List", rate=100)

		self.assertEqual(frappe.db.get_value("Item Price",
			{"price_list": "_Test Price List", "item_code": "_Test Item for Auto Price List"}, "price_list_rate"), None)

		frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 1)

	def test_drop_shipping(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_drop_shipment
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status

		make_stock_entry(target="_Test Warehouse - _TC", qty=10, rate=100)
		from erpnext.stock.doctype.item.test_item import make_item
		po_item = make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})

		dn_item = make_item("_Test Regular Item", {"is_stock_item": 1})

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

		self.assertEqual(so.customer, po.customer)
		self.assertEqual(po.items[0].sales_order, so.name)
		self.assertEqual(po.items[0].item_code, po_item.item_code)
		self.assertEqual(dn.items[0].item_code, dn_item.item_code)

		#test ordered_qty and reserved_qty
		bin = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

		ordered_qty = bin[0].ordered_qty if bin else 0.0
		reserved_qty = bin[0].reserved_qty if bin else 0.0

		self.assertEqual(abs(flt(ordered_qty)), existing_ordered_qty)
		self.assertEqual(abs(flt(reserved_qty)), existing_reserved_qty)

		reserved_qty = frappe.db.get_value("Bin",
					{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEqual(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item + 1)

		#test po_item length
		self.assertEqual(len(po.items), 1)

		#test per_delivered status
		update_status("Delivered", po.name)
		self.assertEqual(flt(frappe.db.get_value("Sales Order", so.name, "per_delivered"), 2), 75.00)

		#test reserved qty after complete delivery
		dn = create_dn_against_so(so.name, delivered_qty=1)
		reserved_qty = frappe.db.get_value("Bin",
			{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEqual(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item)

		#test after closing so
		so.db_set('status', "Closed")
		so.update_reserved_qty()

		bin = frappe.get_all("Bin", filters={"item_code": po_item.item_code, "warehouse": "_Test Warehouse - _TC"},
			fields=["ordered_qty", "reserved_qty"])

		ordered_qty = bin[0].ordered_qty if bin else 0.0
		reserved_qty = bin[0].reserved_qty if bin else 0.0

		self.assertEqual(abs(flt(ordered_qty)), existing_ordered_qty)
		self.assertEqual(abs(flt(reserved_qty)), existing_reserved_qty)

		reserved_qty = frappe.db.get_value("Bin",
			{"item_code": dn_item.item_code, "warehouse": "_Test Warehouse - _TC"}, "reserved_qty")

		self.assertEqual(abs(flt(reserved_qty)), existing_reserved_qty_for_dn_item)

	def test_reserved_qty_for_closing_so(self):
		bin = frappe.get_all("Bin", filters={"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			fields=["reserved_qty"])

		existing_reserved_qty = bin[0].reserved_qty if bin else 0.0

		so = make_sales_order(item_code="_Test Item", qty=1)

		self.assertEqual(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty+1)

		so.update_status("Closed")

		self.assertEqual(get_reserved_qty(item_code="_Test Item", warehouse="_Test Warehouse - _TC"), existing_reserved_qty)

	def test_create_so_with_margin(self):
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		so.items[0].price_list_rate = price_list_rate = 100
		so.items[0].margin_type = 'Percentage'
		so.items[0].margin_rate_or_amount = 25
		so.save()

		new_so = frappe.copy_doc(so)
		new_so.save(ignore_permissions=True)

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))
		new_so.items[0].margin_rate_or_amount = 25
		new_so.payment_schedule = []
		new_so.save()
		new_so.submit()

		self.assertEqual(new_so.get("items")[0].rate, flt((price_list_rate*25)/100 + price_list_rate))

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

	def test_make_work_order(self):
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

		# Raise Work Orders
		po_items= []
		so_item_name= {}
		for item in so.get_work_order_items():
			po_items.append({
				"warehouse": item.get("warehouse"),
				"item_code": item.get("item_code"),
				"pending_qty": item.get("pending_qty"),
				"sales_order_item": item.get("sales_order_item"),
				"bom": item.get("bom")
			})
			so_item_name[item.get("sales_order_item")]= item.get("pending_qty")
		make_work_orders(json.dumps({"items":po_items}), so.name, so.company)

		# Check if Work Orders were raised
		for item in so_item_name:
			wo_qty = frappe.db.sql("select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s", (so.name, item))
			self.assertEquals(wo_qty[0][0], so_item_name.get(item))

	def test_serial_no_based_delivery(self):
		frappe.set_value("Stock Settings", None, "automatically_set_serial_nos_based_on_fifo", 1)
		from erpnext.stock.doctype.item.test_item import make_item
		item = make_item("_Reserved_Serialized_Item", {"is_stock_item": 1,
					"maintain_stock": 1,
					"has_serial_no": 1,
					"serial_no_series": "SI.####",
					"valuation_rate": 500,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		frappe.db.sql("""delete from `tabSerial No` where item_code=%s""", (item.item_code))
		make_item("_Test Item A", {"maintain_stock": 1,
					"valuation_rate": 100,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		make_item("_Test Item B", {"maintain_stock": 1,
					"valuation_rate": 200,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		make_bom(item=item.item_code, rate=1000,
			raw_materials = ['_Test Item A', '_Test Item B'])

		so = make_sales_order(**{
			"item_list": [{
				"item_code": item.item_code,
				"ensure_delivery_based_on_produced_serial_no": 1,
				"qty": 1,
				"rate":1000
			}]
		})
		so.submit()
		from erpnext.manufacturing.doctype.work_order.test_work_order import \
			make_wo_order_test_record
		work_order = make_wo_order_test_record(item=item.item_code,
			qty=1, do_not_save=True)
		work_order.fg_warehouse = "_Test Warehouse - _TC"
		work_order.sales_order = so.name
		work_order.submit()
		make_stock_entry(item_code=item.item_code, target="_Test Warehouse - _TC", qty=1)
		item_serial_no = frappe.get_doc("Serial No", {"item_code": item.item_code})
		from erpnext.manufacturing.doctype.work_order.work_order import \
			make_stock_entry as make_production_stock_entry
		se = frappe.get_doc(make_production_stock_entry(work_order.name, "Manufacture", 1))
		se.submit()
		reserved_serial_no = se.get("items")[2].serial_no
		serial_no_so = frappe.get_value("Serial No", reserved_serial_no, "sales_order")
		self.assertEqual(serial_no_so, so.name)
		dn = make_delivery_note(so.name)
		dn.save()
		self.assertEqual(reserved_serial_no, dn.get("items")[0].serial_no)
		item_line = dn.get("items")[0]
		item_line.serial_no = item_serial_no.name
		self.assertRaises(frappe.ValidationError, dn.submit)
		item_line = dn.get("items")[0]
		item_line.serial_no =  reserved_serial_no
		self.assertTrue(dn.submit)
		dn.load_from_db()
		dn.cancel()
		si = make_sales_invoice(so.name)
		si.update_stock = 1
		si.save()
		self.assertEqual(si.get("items")[0].serial_no, reserved_serial_no)
		item_line = si.get("items")[0]
		item_line.serial_no = item_serial_no.name
		self.assertRaises(frappe.ValidationError, dn.submit)
		item_line = si.get("items")[0]
		item_line.serial_no = reserved_serial_no
		self.assertTrue(si.submit)
		si.submit()
		si.load_from_db()
		si.cancel()
		si = make_sales_invoice(so.name)
		si.update_stock = 0
		si.submit()
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import \
			make_delivery_note as make_delivery_note_from_invoice
		dn = make_delivery_note_from_invoice(si.name)
		dn.save()
		dn.submit()
		self.assertEqual(dn.get("items")[0].serial_no, reserved_serial_no)
		dn.load_from_db()
		dn.cancel()
		si.load_from_db()
		si.cancel()
		se.load_from_db()
		se.cancel()
		self.assertFalse(frappe.db.exists("Serial No", {"sales_order": so.name}))

	def test_request_for_raw_materials(self):
		from erpnext.stock.doctype.item.test_item import make_item
		item = make_item("_Test Finished Item", {"is_stock_item": 1,
			"maintain_stock": 1,
			"valuation_rate": 500,
			"item_defaults": [
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company"
				}]
			})
		make_item("_Test Raw Item A", {"maintain_stock": 1,
					"valuation_rate": 100,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		make_item("_Test Raw Item B", {"maintain_stock": 1,
					"valuation_rate": 200,
					"item_defaults": [
						{
							"default_warehouse": "_Test Warehouse - _TC",
							"company": "_Test Company"
						}]
					})
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		make_bom(item=item.item_code, rate=1000,
			raw_materials = ['_Test Raw Item A', '_Test Raw Item B'])

		so = make_sales_order(**{
			"item_list": [{
				"item_code": item.item_code,
				"qty": 1,
				"rate":1000
			}]
		})
		so.submit()
		mr_dict = frappe._dict()
		items = so.get_work_order_items(1)
		mr_dict['items'] = items
		mr_dict['include_exploded_items'] = 0
		mr_dict['ignore_existing_ordered_qty'] = 1
		make_raw_material_request(mr_dict, so.company, so.name)
		mr = frappe.db.sql("""select name from `tabMaterial Request` ORDER BY creation DESC LIMIT 1""", as_dict=1)[0]
		mr_doc = frappe.get_doc('Material Request',mr.get('name'))
		self.assertEqual(mr_doc.items[0].sales_order, so.name)

	def test_maintain_product_bundle_items_during_sales_cycle(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		make_item("_Test Service Product Bundle_", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 1_", {"is_stock_item": 0})
		make_item("_Test Service Product Bundle Item 2_", {"is_stock_item": 0})

		# NOT CHECKED - CHECKBOX
		frappe.delete_doc("Product Bundle", "_Test Service Product Bundle_")
		make_product_bundle("_Test Service Product Bundle_",
		                    ["_Test Service Product Bundle Item 1_", "_Test Service Product Bundle Item 2_"])
		so = make_sales_order(item_code="_Test Service Product Bundle_", warehouse=None, do_not_submit=True)
		so.maintain_packed_items_list = 0
		so.save()
		so.submit()
		frappe.db.sql("""delete from `tabProduct Bundle Item` where parent = '_Test Service Product Bundle_' and idx = 2""")
		dn = create_dn_against_so(so.name, 1)
		self.assertTrue(dn.submit)

		# CHECKED - CHECKBOX
		frappe.delete_doc("Product Bundle", "_Test Service Product Bundle_")
		make_product_bundle("_Test Service Product Bundle_",
		                    ["_Test Service Product Bundle Item 1_", "_Test Service Product Bundle Item 2_"])
		so2 = make_sales_order(item_code="_Test Service Product Bundle_", warehouse=None, do_not_submit=True)
		so2.maintain_packed_items_list = 1
		so2.save()
		so2.submit()
		frappe.db.sql("""delete from `tabProduct Bundle Item` where parent = '_Test Service Product Bundle_' and idx = 2""")
		dn2 = create_dn_against_so(so2.name, 1)
		self.assertTrue(dn2.submit)

def make_sales_order(**args):
	so = frappe.new_doc("Sales Order")
	args = frappe._dict(args)
	if args.transaction_date:
		so.transaction_date = args.transaction_date

	so.set_warehouse = "" # no need to test set_warehouse permission since it only affects the client
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
