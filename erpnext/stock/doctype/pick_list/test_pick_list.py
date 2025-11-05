# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _dict
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, getdate, nowdate
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.sales_order.sales_order import create_pick_list
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.packed_item.test_packed_item import create_product_bundle
from erpnext.stock.doctype.pick_list.pick_list import create_delivery_note, create_dn_for_pick_lists
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	EmptyStockReconciliationItemsError,
)

test_dependencies = ["Item", "Sales Invoice", "Stock Entry", "Batch"]


class TestPickList(FrappeTestCase):
	def test_pick_list_picks_warehouse_for_each_item(self):
		item_code = make_item().name
		try:
			frappe.get_doc(
				{
					"doctype": "Stock Reconciliation",
					"company": "_Test Company",
					"purpose": "Opening Stock",
					"expense_account": "Temporary Opening - _TC",
					"items": [
						{
							"item_code": item_code,
							"warehouse": "_Test Warehouse - _TC",
							"valuation_rate": 100,
							"qty": 5,
						}
					],
				}
			).submit()
		except EmptyStockReconciliationItemsError:
			pass

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": item_code,
						"qty": 5,
						"stock_qty": 5,
						"conversion_factor": 1,
						"sales_order": "_T-Sales Order-1",
						"sales_order_item": "_T-Sales Order-1_item",
					}
				],
			}
		)
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, item_code)
		self.assertEqual(pick_list.locations[0].warehouse, "_Test Warehouse - _TC")
		self.assertEqual(pick_list.locations[0].qty, 5)

	def test_pick_list_splits_row_according_to_warehouse_availability(self):
		try:
			frappe.get_doc(
				{
					"doctype": "Stock Reconciliation",
					"company": "_Test Company",
					"purpose": "Opening Stock",
					"expense_account": "Temporary Opening - _TC",
					"items": [
						{
							"item_code": "_Test Item Warehouse Group Wise Reorder",
							"warehouse": "_Test Warehouse Group-C1 - _TC",
							"valuation_rate": 100,
							"qty": 5,
						}
					],
				}
			).submit()
		except EmptyStockReconciliationItemsError:
			pass

		try:
			frappe.get_doc(
				{
					"doctype": "Stock Reconciliation",
					"company": "_Test Company",
					"purpose": "Opening Stock",
					"expense_account": "Temporary Opening - _TC",
					"items": [
						{
							"item_code": "_Test Item Warehouse Group Wise Reorder",
							"warehouse": "_Test Warehouse 2 - _TC",
							"valuation_rate": 400,
							"qty": 10,
						}
					],
				}
			).submit()
		except EmptyStockReconciliationItemsError:
			pass

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": "_Test Item Warehouse Group Wise Reorder",
						"qty": 1000,
						"stock_qty": 1000,
						"conversion_factor": 1,
						"sales_order": "_T-Sales Order-1",
						"sales_order_item": "_T-Sales Order-1_item",
					}
				],
			}
		)

		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, "_Test Item Warehouse Group Wise Reorder")
		self.assertEqual(pick_list.locations[0].warehouse, "_Test Warehouse Group-C1 - _TC")
		self.assertEqual(pick_list.locations[0].qty, 5)

		self.assertEqual(pick_list.locations[1].item_code, "_Test Item Warehouse Group Wise Reorder")
		self.assertEqual(pick_list.locations[1].warehouse, "_Test Warehouse 2 - _TC")
		self.assertEqual(pick_list.locations[1].qty, 10)

	def test_pick_list_shows_serial_no_for_serialized_item(self):
		serial_nos = ["SADD-0001", "SADD-0002", "SADD-0003", "SADD-0004", "SADD-0005"]

		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"company": "_Test Company",
						"item_code": "_Test Serialized Item",
						"serial_no": serial_no,
					}
				).insert()

		stock_reconciliation = frappe.get_doc(
			{
				"doctype": "Stock Reconciliation",
				"purpose": "Stock Reconciliation",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Serialized Item",
						"warehouse": "_Test Warehouse - _TC",
						"valuation_rate": 100,
						"reconcile_all_serial_batch": 1,
						"qty": 5,
						"serial_and_batch_bundle": make_serial_batch_bundle(
							frappe._dict(
								{
									"item_code": "_Test Serialized Item",
									"warehouse": "_Test Warehouse - _TC",
									"qty": 5,
									"rate": 100,
									"type_of_transaction": "Inward",
									"do_not_submit": True,
									"voucher_type": "Stock Reconciliation",
									"serial_nos": serial_nos,
								}
							)
						).name,
					}
				],
			}
		)

		try:
			stock_reconciliation.submit()
		except EmptyStockReconciliationItemsError:
			pass

		so = make_sales_order(
			item_code="_Test Serialized Item", warehouse="_Test Warehouse - _TC", qty=5, rate=1000
		)

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": "_Test Serialized Item",
						"qty": 1000,
						"stock_qty": 1000,
						"conversion_factor": 1,
						"sales_order": so.name,
						"sales_order_item": so.items[0].name,
					}
				],
			}
		)

		pick_list.save()
		pick_list.submit()

		self.assertEqual(pick_list.locations[0].item_code, "_Test Serialized Item")
		self.assertEqual(pick_list.locations[0].warehouse, "_Test Warehouse - _TC")
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(
			get_serial_nos_from_bundle(pick_list.locations[0].serial_and_batch_bundle), serial_nos
		)

	def test_pick_list_shows_batch_no_for_batched_item(self):
		# check if oldest batch no is picked
		item = frappe.db.exists("Item", {"item_name": "Batched Item"})
		if not item:
			item = create_item("Batched Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.batch_number_series = "B-BATCH-.##"
			item.save()
		else:
			item = frappe.get_doc("Item", {"item_name": "Batched Item"})

		pr1 = make_purchase_receipt(item_code="Batched Item", qty=1, rate=100.0)

		pr1.load_from_db()
		oldest_batch_no = get_batch_from_bundle(pr1.items[0].serial_and_batch_bundle)

		pr2 = make_purchase_receipt(item_code="Batched Item", qty=2, rate=100.0)

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"purpose": "Material Transfer",
				"locations": [
					{
						"item_code": "Batched Item",
						"qty": 1,
						"stock_qty": 1,
						"conversion_factor": 1,
					}
				],
			}
		)
		pick_list.set_item_locations()
		self.assertEqual(pick_list.locations[0].batch_no, oldest_batch_no)

		pr1.cancel()
		pr2.cancel()

	def test_pick_list_for_batched_and_serialised_item(self):
		# check if oldest batch no and serial nos are picked
		item = frappe.db.exists("Item", {"item_name": "Batched and Serialised Item"})
		if not item:
			item = create_item("Batched and Serialised Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "B-BATCH-.##"
			item.serial_no_series = "S-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {"item_name": "Batched and Serialised Item"})

		pr1 = make_purchase_receipt(item_code="Batched and Serialised Item", qty=2, rate=100.0)

		pr1.load_from_db()
		oldest_batch_no = get_batch_from_bundle(pr1.items[0].serial_and_batch_bundle)
		oldest_serial_nos = get_serial_nos_from_bundle(pr1.items[0].serial_and_batch_bundle)

		pr2 = make_purchase_receipt(item_code="Batched and Serialised Item", qty=2, rate=100.0)

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"purpose": "Material Transfer",
				"locations": [
					{
						"item_code": "Batched and Serialised Item",
						"qty": 2,
						"stock_qty": 2,
						"conversion_factor": 1,
					}
				],
			}
		)
		pick_list.set_item_locations()
		pick_list.submit()
		pick_list.reload()

		self.assertEqual(
			get_batch_from_bundle(pick_list.locations[0].serial_and_batch_bundle), oldest_batch_no
		)
		self.assertEqual(
			get_serial_nos_from_bundle(pick_list.locations[0].serial_and_batch_bundle), oldest_serial_nos
		)

		pick_list.cancel()
		pr1.cancel()
		pr2.cancel()

	def test_pick_list_for_items_from_multiple_sales_orders(self):
		item_code = make_item().name
		try:
			frappe.get_doc(
				{
					"doctype": "Stock Reconciliation",
					"company": "_Test Company",
					"purpose": "Opening Stock",
					"expense_account": "Temporary Opening - _TC",
					"items": [
						{
							"item_code": item_code,
							"warehouse": "_Test Warehouse - _TC",
							"valuation_rate": 100,
							"qty": 10,
						}
					],
				}
			).submit()
		except EmptyStockReconciliationItemsError:
			pass

		sales_order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"qty": 10,
						"delivery_date": frappe.utils.today(),
						"warehouse": "_Test Warehouse - _TC",
					}
				],
			}
		)
		sales_order.submit()

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": item_code,
						"qty": 5,
						"stock_qty": 5,
						"conversion_factor": 1,
						"sales_order": "_T-Sales Order-1",
						"sales_order_item": "_T-Sales Order-1_item",
					},
					{
						"item_code": item_code,
						"qty": 5,
						"stock_qty": 5,
						"conversion_factor": 1,
						"sales_order": sales_order.name,
						"sales_order_item": sales_order.items[0].name,
					},
				],
			}
		)
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, item_code)
		self.assertEqual(pick_list.locations[0].warehouse, "_Test Warehouse - _TC")
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(pick_list.locations[0].sales_order_item, "_T-Sales Order-1_item")

		self.assertEqual(pick_list.locations[1].item_code, item_code)
		self.assertEqual(pick_list.locations[1].warehouse, "_Test Warehouse - _TC")
		self.assertEqual(pick_list.locations[1].qty, 5)
		self.assertEqual(pick_list.locations[1].sales_order_item, sales_order.items[0].name)

	def test_pick_list_for_items_with_multiple_UOM(self):
		item_code = make_item(
			uoms=[
				{"uom": "Nos", "conversion_factor": 1},
				{"uom": "Hand", "conversion_factor": 5},
				{"uom": "Unit", "conversion_factor": 0.5},
			]
		).name
		purchase_receipt = make_purchase_receipt(item_code=item_code, qty=10)
		purchase_receipt.submit()

		sales_order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": item_code,
						"qty": 1,
						"uom": "Hand",
						"delivery_date": frappe.utils.today(),
						"warehouse": "_Test Warehouse - _TC",
					},
					{
						"item_code": item_code,
						"qty": 1,
						"conversion_factor": 1,
						"delivery_date": frappe.utils.today(),
						"warehouse": "_Test Warehouse - _TC",
					},
				],
			}
		).insert()
		sales_order.submit()

		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": item_code,
						"qty": 2,
						"stock_qty": 1,
						"uom": "Unit",
						"conversion_factor": 0.5,
						"sales_order": sales_order.name,
						"sales_order_item": sales_order.items[0].name,
					},
					{
						"item_code": item_code,
						"qty": 1,
						"stock_qty": 1,
						"conversion_factor": 1,
						"sales_order": sales_order.name,
						"sales_order_item": sales_order.items[1].name,
					},
				],
			}
		)
		pick_list.set_item_locations()
		pick_list.submit()

		delivery_note = create_delivery_note(pick_list.name)
		pick_list.load_from_db()

		#  pick list stk_qty / dn conversion_factor = dn qty (1/5 = 0.2)
		self.assertEqual(
			pick_list.locations[0].picked_qty,
			delivery_note.items[0].qty * delivery_note.items[0].conversion_factor,
		)
		self.assertEqual(pick_list.locations[1].qty, delivery_note.items[1].qty)
		self.assertEqual(sales_order.items[0].conversion_factor, delivery_note.items[0].conversion_factor)

		pick_list.cancel()
		sales_order.cancel()
		purchase_receipt.cancel()

	def test_pick_list_grouping_before_print(self):
		def _compare_dicts(a, b):
			"compare dicts but ignore missing keys in `a`"
			for key, value in a.items():
				self.assertEqual(b.get(key), value, msg=f"{key} doesn't match")

		# nothing should be grouped
		pl = frappe.get_doc(
			doctype="Pick List",
			group_same_items=True,
			locations=[
				_dict(item_code="A", warehouse="X", qty=1, picked_qty=2),
				_dict(item_code="B", warehouse="X", qty=1, picked_qty=2),
				_dict(item_code="A", warehouse="Y", qty=1, picked_qty=2),
				_dict(item_code="B", warehouse="Y", qty=1, picked_qty=2),
			],
		)
		pl.before_print()
		self.assertEqual(len(pl.locations), 4)

		# grouping should not happen if group_same_items is False
		pl = frappe.get_doc(
			doctype="Pick List",
			group_same_items=False,
			locations=[
				_dict(item_code="A", warehouse="X", qty=5, picked_qty=1),
				_dict(item_code="B", warehouse="Y", qty=4, picked_qty=2),
				_dict(item_code="A", warehouse="X", qty=3, picked_qty=2),
				_dict(item_code="B", warehouse="Y", qty=2, picked_qty=2),
			],
		)
		pl.before_print()
		self.assertEqual(len(pl.locations), 4)

		# grouping should halve the number of items
		pl.group_same_items = True
		pl.before_print()
		self.assertEqual(len(pl.locations), 2)

		expected_items = [
			_dict(item_code="A", warehouse="X", qty=8, picked_qty=3),
			_dict(item_code="B", warehouse="Y", qty=6, picked_qty=4),
		]
		for expected_item, created_item in zip(expected_items, pl.locations, strict=False):
			_compare_dicts(expected_item, created_item)

	def test_multiple_dn_creation(self):
		sales_order_1 = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"conversion_factor": 1,
						"delivery_date": frappe.utils.today(),
					}
				],
			}
		).insert()
		sales_order_1.submit()
		sales_order_2 = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer 1",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Item 2",
						"qty": 1,
						"conversion_factor": 1,
						"delivery_date": frappe.utils.today(),
					},
				],
			}
		).insert()
		sales_order_2.submit()
		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"items_based_on": "Sales Order",
				"purpose": "Delivery",
				"customer": "_Test Customer",
				"locations": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"stock_qty": 1,
						"conversion_factor": 1,
						"sales_order": sales_order_1.name,
						"sales_order_item": sales_order_1.items[0].name,
					},
					{
						"item_code": "_Test Item 2",
						"qty": 1,
						"stock_qty": 1,
						"conversion_factor": 1,
						"sales_order": sales_order_2.name,
						"sales_order_item": sales_order_2.items[0].name,
					},
				],
			}
		)
		pick_list.set_item_locations()
		pick_list.submit()
		create_delivery_note(pick_list.name)
		for dn in frappe.get_all(
			"Delivery Note",
			filters={"against_pick_list": pick_list.name, "customer": "_Test Customer"},
			fields={"name"},
		):
			for dn_item in frappe.get_doc("Delivery Note", dn.name).get("items"):
				self.assertEqual(dn_item.item_code, "_Test Item")
				self.assertEqual(dn_item.against_sales_order, sales_order_1.name)
				self.assertEqual(dn_item.against_pick_list, pick_list.name)
				self.assertEqual(dn_item.pick_list_item, pick_list.locations[0].name)

		for dn in frappe.get_all(
			"Delivery Note",
			filters={"against_pick_list": pick_list.name, "customer": "_Test Customer 1"},
			fields={"name"},
		):
			for dn_item in frappe.get_doc("Delivery Note", dn.name).get("items"):
				self.assertEqual(dn_item.item_code, "_Test Item 2")
				self.assertEqual(dn_item.against_sales_order, sales_order_2.name)
				self.assertEqual(dn_item.against_pick_list, pick_list.name)
				self.assertEqual(dn_item.pick_list_item, pick_list.locations[1].name)
		# test DN creation without so
		pick_list_1 = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"purpose": "Delivery",
				"locations": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"stock_qty": 1,
						"conversion_factor": 1,
					},
					{
						"item_code": "_Test Item 2",
						"qty": 2,
						"stock_qty": 2,
						"conversion_factor": 1,
					},
				],
			}
		)
		pick_list_1.set_item_locations()
		pick_list_1.submit()
		create_delivery_note(pick_list_1.name)
		for dn in frappe.get_all(
			"Delivery Note", filters={"against_pick_list": pick_list_1.name}, fields={"name"}
		):
			for dn_item in frappe.get_doc("Delivery Note", dn.name).get("items"):
				if dn_item.item_code == "_Test Item":
					self.assertEqual(dn_item.qty, 1)
				if dn_item.item_code == "_Test Item 2":
					self.assertEqual(dn_item.qty, 2)

	def test_picklist_with_multi_uom(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(properties={"uoms": [dict(uom="Box", conversion_factor=24)]}).name
		make_stock_entry(item=item, to_warehouse=warehouse, qty=1000)

		so = make_sales_order(item_code=item, qty=10, rate=42, uom="Box")
		pl = create_pick_list(so.name)
		# pick half the qty
		for loc in pl.locations:
			loc.picked_qty = loc.stock_qty / 2
		pl.save()
		pl.submit()

		so.reload()
		self.assertEqual(so.per_picked, 50)

	def test_picklist_for_batch_item(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "PICKLT-.######"}
		).name

		# create batch
		for batch_id in ["PICKLT-000001", "PICKLT-000002"]:
			if not frappe.db.exists("Batch", batch_id):
				frappe.get_doc(
					{
						"doctype": "Batch",
						"batch_id": batch_id,
						"item": item,
					}
				).insert()

		make_stock_entry(
			item=item,
			to_warehouse=warehouse,
			qty=50,
			basic_rate=100,
			batches=frappe._dict({"PICKLT-000001": 30, "PICKLT-000002": 20}),
		)

		so = make_sales_order(item_code=item, qty=25.0, rate=100)
		pl = create_pick_list(so.name)
		pl.submit()
		# pick half the qty
		for loc in pl.locations:
			self.assertEqual(loc.qty, 25.0)
			self.assertTrue(loc.serial_and_batch_bundle)

		pl.save()
		pl.submit()

		so1 = make_sales_order(item_code=item, qty=10.0, rate=100)
		pl1 = create_pick_list(so1.name)
		pl1.submit()

		# pick half the qty
		for loc in pl1.locations:
			self.assertEqual(loc.qty, 5.0)
			self.assertTrue(loc.serial_and_batch_bundle)

			data = frappe.get_all(
				"Serial and Batch Entry",
				fields=["qty", "batch_no"],
				filters={"parent": loc.serial_and_batch_bundle},
			)

			for d in data:
				self.assertTrue(d.batch_no in ["PICKLT-000001", "PICKLT-000002"])
				if d.batch_no == "PICKLT-000001":
					self.assertEqual(d.qty, 5.0 * -1)
				elif d.batch_no == "PICKLT-000002":
					self.assertEqual(d.qty, 5.0 * -1)

		pl1.cancel()
		pl.cancel()

	def test_picklist_for_serial_item(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SN-PICKLT-.######"}
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=50, basic_rate=100)

		so = make_sales_order(item_code=item, qty=25.0, rate=100)
		pl = create_pick_list(so.name)
		pl.submit()
		picked_serial_nos = []
		# pick half the qty
		for loc in pl.locations:
			self.assertEqual(loc.qty, 25.0)
			self.assertTrue(loc.serial_and_batch_bundle)

			data = frappe.get_all(
				"Serial and Batch Entry",
				fields=["serial_no"],
				filters={"parent": loc.serial_and_batch_bundle},
			)

			picked_serial_nos = [d.serial_no for d in data]
			self.assertEqual(len(picked_serial_nos), 25)

		so1 = make_sales_order(item_code=item, qty=10.0, rate=100)
		pl1 = create_pick_list(so1.name)
		pl1.submit()
		# pick half the qty
		for loc in pl1.locations:
			self.assertEqual(loc.qty, 10.0)
			self.assertTrue(loc.serial_and_batch_bundle)

			data = frappe.get_all(
				"Serial and Batch Entry",
				fields=["qty", "batch_no"],
				filters={"parent": loc.serial_and_batch_bundle},
			)

			self.assertEqual(len(data), 10)
			for d in data:
				self.assertTrue(d.serial_no not in picked_serial_nos)

		pl1.cancel()
		pl.cancel()

	def test_picklist_with_bundles(self):
		warehouse = "_Test Warehouse - _TC"

		quantities = [5, 2]
		bundle, components = create_product_bundle(quantities, warehouse=warehouse)
		bundle_items = dict(zip(components, quantities, strict=False))

		so = make_sales_order(item_code=bundle, qty=3, rate=42)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(len(pl.locations), 2)
		for item in pl.locations:
			self.assertEqual(item.stock_qty, bundle_items[item.item_code] * 3)

		# check picking status on sales order
		pl.submit()
		so.reload()
		self.assertEqual(so.per_picked, 100)

		# deliver
		dn = create_delivery_note(pl.name).submit()
		self.assertEqual(dn.items[0].rate, 42)
		self.assertEqual(dn.packed_items[0].warehouse, warehouse)
		so.reload()
		self.assertEqual(so.per_delivered, 100)

	def test_picklist_with_partial_bundles(self):
		# from test_records.json
		warehouse = "_Test Warehouse - _TC"

		quantities = [5, 2]
		bundle, components = create_product_bundle(quantities, warehouse=warehouse)

		so = make_sales_order(item_code=bundle, qty=4, rate=42)

		pl = create_pick_list(so.name)
		for loc in pl.locations:
			loc.picked_qty = loc.qty / 2

		pl.save().submit()
		so.reload()
		self.assertEqual(so.per_picked, 50)

		# deliver half qty
		dn = create_delivery_note(pl.name).submit()
		self.assertEqual(dn.items[0].rate, 42)
		so.reload()
		self.assertEqual(so.per_delivered, 50)

		pl = create_pick_list(so.name)
		pl.save().submit()
		so.reload()
		self.assertEqual(so.per_picked, 100)

		# deliver remaining
		dn = create_delivery_note(pl.name).submit()
		self.assertEqual(dn.items[0].rate, 42)
		so.reload()
		self.assertEqual(so.per_delivered, 100)

	def test_pick_list_status(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item=item, to_warehouse=warehouse, qty=10)

		so = make_sales_order(item_code=item, qty=10, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		pl.reload()
		self.assertEqual(pl.status, "Draft")

		pl.submit()
		pl.reload()
		self.assertEqual(pl.status, "Open")

		dn = create_delivery_note(pl.name)
		dn.save()
		pl.reload()
		self.assertEqual(pl.status, "Open")

		dn.submit()
		pl.reload()
		self.assertEqual(pl.status, "Completed")

		dn.cancel()
		pl.reload()
		self.assertEqual(pl.status, "Open")

		pl.cancel()
		pl.reload()
		self.assertEqual(pl.status, "Cancelled")

	def test_pick_list_validation(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item("Test Non Serialized Pick List Item", properties={"is_stock_item": 1}).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=10)

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		pl.submit()
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=4, rate=100)
		pl = create_pick_list(so.name)
		self.assertFalse(hasattr(pl, "locations"))

	def test_pick_list_validation_for_serial_no(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Serialized Pick List Item",
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SN-SPLI-.####"},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=10)

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.locations[0].qty = 5
		pl.save()
		pl.submit()
		self.assertTrue(pl.locations[0].serial_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertTrue(pl.locations[0].serial_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=4, rate=100)
		pl = create_pick_list(so.name)
		self.assertFalse(hasattr(pl, "locations"))

	def test_pick_list_validation_for_batch_no(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Batch Pick List Item",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BATCH-SPLI-.####",
				"create_new_batch": 1,
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=10)

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.locations[0].qty = 5
		pl.save()
		pl.submit()
		self.assertTrue(pl.locations[0].batch_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertTrue(pl.locations[0].batch_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=4, rate=100)
		pl = create_pick_list(so.name)
		self.assertFalse(hasattr(pl, "locations"))

	def test_pick_list_validation_for_batch_no_and_serial_item(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Serialized Batch Pick List Item",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "SN-BT-BATCH-SPLI-.####",
				"create_new_batch": 1,
				"has_serial_no": 1,
				"serial_no_series": "SN-BT-SPLI-.####",
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=10)

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.locations[0].qty = 5
		pl.save()
		pl.submit()
		self.assertTrue(pl.locations[0].batch_no)
		self.assertTrue(pl.locations[0].serial_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=5, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertTrue(pl.locations[0].batch_no)
		self.assertTrue(pl.locations[0].serial_no)
		self.assertEqual(pl.locations[0].qty, 5.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=4, rate=100)
		pl = create_pick_list(so.name)
		self.assertFalse(hasattr(pl, "locations"))

	def test_pick_list_validation_for_multiple_batches_and_sales_order(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Batch Pick List Item For Multiple Batches",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "SN-BT-BATCH-SPLIMBATCH-.####",
				"create_new_batch": 1,
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=5)
		make_stock_entry(item=item, to_warehouse=warehouse, qty=5)

		so = make_sales_order(item_code=item, qty=6, rate=100)

		pl1 = create_pick_list(so.name)
		pl1.save()
		self.assertEqual(pl1.locations[0].qty, 5.0)
		self.assertEqual(pl1.locations[1].qty, 1.0)

		so = make_sales_order(item_code=item, qty=4, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(pl.locations[0].qty, 4.0)
		self.assertTrue(hasattr(pl, "locations"))

		pl1.submit()

		pl.reload()
		pl.submit()
		self.assertEqual(pl.locations[0].qty, 4.0)
		self.assertTrue(hasattr(pl, "locations"))

	def test_pick_list_for_multiple_sales_order_with_multiple_batches(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Batch Pick List Item For Multiple Batches and Sales Order",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "SN-SOO-BT-SPLIMBATCH-.####",
				"create_new_batch": 1,
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)
		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)

		so = make_sales_order(item_code=item, qty=10, rate=100)

		pl1 = create_pick_list(so.name)
		pl1.save()
		self.assertEqual(pl1.locations[0].qty, 10)

		so = make_sales_order(item_code=item, qty=110, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(pl.locations[0].qty, 90.0)
		self.assertEqual(pl.locations[1].qty, 20.0)
		self.assertTrue(hasattr(pl, "locations"))

		pl1.submit()

		pl.reload()
		pl.submit()
		self.assertEqual(pl.locations[0].qty, 90.0)
		self.assertEqual(pl.locations[1].qty, 20.0)
		self.assertTrue(hasattr(pl, "locations"))

	def test_pick_list_for_multiple_sales_order_with_multiple_serial_nos(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Serial No Pick List Item For Multiple Batches and Sales Order",
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SNNN-SOO-BT-SPLIMBATCH-.####",
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)
		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)

		so = make_sales_order(item_code=item, qty=10, rate=100)

		pl1 = create_pick_list(so.name)
		pl1.save()
		self.assertEqual(pl1.locations[0].qty, 10)

		serial_nos = pl1.locations[0].serial_no.split("\n")
		self.assertEqual(len(serial_nos), 10)

		so = make_sales_order(item_code=item, qty=110, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(pl.locations[0].qty, 110.0)
		self.assertTrue(hasattr(pl, "locations"))

		new_serial_nos = pl.locations[0].serial_no.split("\n")
		self.assertEqual(len(new_serial_nos), 110)

		for sn in serial_nos:
			self.assertFalse(sn in new_serial_nos)

		pl1.submit()

		pl.reload()
		pl.submit()
		self.assertEqual(pl.locations[0].qty, 110.0)
		self.assertTrue(hasattr(pl, "locations"))

	def test_pick_list_for_multiple_sales_orders_for_non_serialized_item(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Non Serialized Pick List Item For Multiple Batches and Sales Order",
			properties={
				"is_stock_item": 1,
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)
		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)

		so = make_sales_order(item_code=item, qty=10, rate=100)

		pl1 = create_pick_list(so.name)
		pl1.save()
		self.assertEqual(pl1.locations[0].qty, 10)

		so = make_sales_order(item_code=item, qty=110, rate=100)

		pl = create_pick_list(so.name)
		pl.save()
		self.assertEqual(pl.locations[0].qty, 110.0)
		self.assertTrue(hasattr(pl, "locations"))

		pl1.submit()

		pl.reload()
		pl.submit()
		self.assertEqual(pl.locations[0].qty, 110.0)
		self.assertTrue(hasattr(pl, "locations"))

		so = make_sales_order(item_code=item, qty=110, rate=100)
		pl = create_pick_list(so.name)
		pl.save()

		self.assertEqual(pl.locations[0].qty, 80.0)

	def test_validate_picked_qty_with_manual_option(self):
		warehouse = "_Test Warehouse - _TC"
		non_serialized_item = make_item(
			"Test Non Serialized Pick List Item For Manual Option", properties={"is_stock_item": 1}
		).name

		serialized_item = make_item(
			"Test Serialized Pick List Item For Manual Option",
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SN-HSNMSPLI-.####"},
		).name

		batched_item = make_item(
			"Test Batched Pick List Item For Manual Option",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "SN-HBNMSPLI-.####",
				"create_new_batch": 1,
			},
		).name

		make_stock_entry(item=non_serialized_item, to_warehouse=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item=serialized_item, to_warehouse=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item=batched_item, to_warehouse=warehouse, qty=10, basic_rate=100)

		so = make_sales_order(
			item_code=non_serialized_item, qty=10, rate=100, do_not_save=True, warehouse=warehouse
		)
		so.append("items", {"item_code": serialized_item, "qty": 10, "rate": 100, "warehouse": warehouse})
		so.append("items", {"item_code": batched_item, "qty": 10, "rate": 100, "warehouse": warehouse})
		so.set_missing_values()
		so.save()
		so.submit()

		pl = create_pick_list(so.name)
		pl.pick_manually = 1

		for row in pl.locations:
			row.qty = row.qty + 10

		self.assertRaises(frappe.ValidationError, pl.save)

	def test_over_allowance_picking(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			"Test Over Allowance Picking Item",
			properties={
				"is_stock_item": 1,
			},
		).name

		make_stock_entry(item=item, to_warehouse=warehouse, qty=100)

		so = make_sales_order(item_code=item, qty=10, rate=100)

		pl_doc = create_pick_list(so.name)
		pl_doc.save()
		self.assertEqual(pl_doc.locations[0].qty, 10)

		pl_doc.locations[0].qty = 15
		pl_doc.locations[0].stock_qty = 15
		pl_doc.save()

		self.assertEqual(pl_doc.locations[0].qty, 15)
		self.assertRaises(frappe.ValidationError, pl_doc.submit)

		frappe.db.set_single_value("Stock Settings", "over_picking_allowance", 50)

		pl_doc.reload()
		pl_doc.submit()

		frappe.db.set_single_value("Stock Settings", "over_picking_allowance", 0)

	def test_ignore_pricing_rule_in_pick_list(self):
		frappe.flags.print_stmt = False
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "IPR-PICKLT-.######",
				"create_new_batch": 1,
			}
		).name

		make_stock_entry(
			item=item,
			to_warehouse=warehouse,
			qty=2,
			basic_rate=100,
		)

		pricing_rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "Same Free Item",
				"price_or_product_discount": "Product",
				"selling": 1,
				"apply_on": "Item Code",
				"items": [
					{
						"item_code": item,
					}
				],
				"same_item": 1,
				"is_recursive": 1,
				"recurse_for": 2,
				"free_qty": 1,
				"enforce_free_item_qty": 1,
				"dont_enforce_free_item_qty": 0,
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		)

		pricing_rule.save()
		frappe.flags.print_stmt = True

		so = make_sales_order(item_code=item, qty=2, rate=100, do_not_save=True)
		so.set_warehouse = warehouse
		so.submit()

		self.assertEqual(len(so.items), 2)
		self.assertTrue(so.items[1].is_free_item)

		pl = create_pick_list(so.name)
		pl.ignore_pricing_rule = 1
		pl.save()
		pl.submit()

		self.assertEqual(len(pl.locations), 1)

		delivery_note = create_delivery_note(pl.name)

		self.assertEqual(len(delivery_note.items), 1)

	def test_pick_list_to_unreservation_TC_S_072(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1)
		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=5, rate=4000)

		sales_order = make_sales_order(item_code="_Test Item Home Desktop 100", qty=4, rate=5000)
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		pick_list = create_pick_list(sales_order.name)
		pick_list.save()
		pick_list.submit()
		so_items_details_map = {}
		for location in pick_list.locations:
			if location.warehouse and location.sales_order and location.sales_order_item:
				item_details = {
					"sales_order_item": location.sales_order_item,
					"item_code": location.item_code,
					"warehouse": location.warehouse,
					"qty_to_reserve": (flt(location.picked_qty) - flt(location.stock_reserved_qty)),
					"from_voucher_no": location.parent,
					"from_voucher_detail_no": location.name,
					"serial_and_batch_bundle": location.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(location.sales_order, []).append(item_details)

		if so_items_details_map:
			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_doc("Sales Order", so)
				so_doc.create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Pick List",
					notify=None,
				)

		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so_doc.name}, "status"), "Reserved"
		)

		cancel_stock_reservation_entries(
			from_voucher_type="Pick List", from_voucher_no=pick_list.name, notify=False
		)
		self.assertEqual(
			frappe.db.get_value("Stock Reservation Entry", {"voucher_no": so_doc.name}, "status"), "Cancelled"
		)

	def test_quotation_to_sales_invoice_with_pick_list_TC_S_085(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=4000)
		quotation = make_quotation(
			item="_Test Item Home Desktop 100",
			qty=4,
			rate=5000,
			warehouse="Stores - _TC",
		)
		quotation.save()
		quotation.submit()
		self.assertEqual(quotation.status, "Open")

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(nowdate(), 5)
		sales_order.insert()
		sales_order.submit()

		self.assertEqual(sales_order.status, "To Deliver and Bill")
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")
		# Pick list
		pick_list = create_pick_list(sales_order.name)
		pick_list.save()
		pick_list.submit()
		# Delivery note
		delivery_note = create_delivery_note(pick_list.name)
		delivery_note.save()
		delivery_note.submit()

		stock_check(self, delivery_note.name, -4)

		# sales invoice
		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.insert()
		sales_invoice.submit()
		validate_gl_entries(self, sales_invoice.name, 20000)

	def test_sales_order_to_sales_invoice_with_pick_list_TC_S_086(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=5, rate=4000)

		sales_order = make_sales_order(item_code="_Test Item Home Desktop 100", qty=4, rate=5000)
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		# Pick list
		pick_list = create_pick_list(sales_order.name)
		pick_list.save()
		pick_list.submit()
		# Delivery note
		delivery_note = create_delivery_note(pick_list.name)
		delivery_note.save()
		delivery_note.submit()

		stock_check(self, delivery_note.name, -4)

		# sales invoice
		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.insert()
		sales_invoice.submit()
		validate_gl_entries(self, sales_invoice.name, 20000)

	def test_sales_order_to_sales_invoice_with_double_entries_TC_S_087(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=5, rate=4000)

		sales_order = make_sales_order(item_code="_Test Item Home Desktop 100", qty=4, rate=5000)
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		# Pick list
		pick_list_1 = create_pick_list(sales_order.name)
		pick_list_1.save()
		for i in pick_list_1.locations:
			i.qty = 2
			i.stock_qty = 2
		pick_list_1.submit()
		# Delivery note
		delivery_note_1 = create_delivery_note(pick_list_1.name)
		delivery_note_1.save()
		delivery_note_1.submit()

		stock_check(self, delivery_note_1.name, -2)

		# sales invoice
		sales_invoice_1 = make_sales_invoice(delivery_note_1.name)
		sales_invoice_1.insert()
		sales_invoice_1.submit()
		validate_gl_entries(self, sales_invoice_1.name, 10000)

		delivery_note_1.reload()
		self.assertEqual(sales_invoice_1.status, "Unpaid")
		self.assertEqual(delivery_note_1.status, "Completed")

		# Pick list
		pick_list_2 = create_pick_list(sales_order.name)
		pick_list_2.save()
		for i in pick_list_2.locations:
			i.qty = 2
			i.stock_qty = 2
		pick_list_2.submit()
		# Delivery note
		delivery_note_2 = create_delivery_note(pick_list_2.name)
		delivery_note_2.save()
		delivery_note_2.submit()

		stock_check(self, delivery_note_2.name, -2)

		# sales invoice
		sales_invoice_2 = make_sales_invoice(delivery_note_2.name)
		sales_invoice_2.insert()
		sales_invoice_2.submit()
		validate_gl_entries(self, sales_invoice_2.name, 10000)

		sales_order.reload()
		delivery_note_2.reload()
		self.assertEqual(sales_invoice_2.status, "Unpaid")
		self.assertEqual(sales_order.status, "Completed")
		self.assertEqual(delivery_note_2.status, "Completed")

	def test_sales_order_to_sales_invoice_with_2_SI_TC_S_088(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=5, rate=4000)

		sales_order = make_sales_order(item_code="_Test Item Home Desktop 100", qty=4, rate=5000)
		self.assertEqual(sales_order.status, "To Deliver and Bill")

		# Pick list
		pick_list = create_pick_list(sales_order.name)
		pick_list.save()
		pick_list.submit()
		# Delivery note
		delivery_note = create_delivery_note(pick_list.name)
		delivery_note.save()
		delivery_note.submit()

		stock_check(self, delivery_note.name, -4)
		self.assertEqual(delivery_note.status, "To Bill")

		# sales invoice
		sales_invoice_1 = make_sales_invoice(delivery_note.name)
		for i in sales_invoice_1.items:
			i.qty = 2
		sales_invoice_1.insert()
		sales_invoice_1.submit()
		validate_gl_entries(self, sales_invoice_1.name, 10000)
		self.assertEqual(sales_invoice_1.status, "Unpaid")

		sales_invoice_2 = make_sales_invoice(delivery_note.name)
		for i in sales_invoice_2.items:
			i.qty = 2
		sales_invoice_2.insert()
		sales_invoice_2.submit()
		validate_gl_entries(self, sales_invoice_2.name, 10000)
		self.assertEqual(sales_invoice_2.status, "Unpaid")

		sales_order.reload()
		delivery_note.reload()
		self.assertEqual(sales_order.status, "Completed")
		self.assertEqual(delivery_note.status, "Completed")

	def test_update_stock_entry_items_with_no_reference_TC_SCK_462(self):
		from erpnext.stock.doctype.pick_list.pick_list import (
			update_common_item_properties,
			update_stock_entry_items_with_no_reference,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

		# Create dummy Pick List with multiple locations
		pick_list = frappe.new_doc("Pick List")
		pick_list.company = "_Test Company"

		# Add fake location entries
		pick_list.locations = [
			frappe._dict(
				{
					"item_code": "_Test Item",
					"qty": 2,
					"uom": "Nos",
					"warehouse": "_Test Warehouse",
					"batch_no": None,
					"serial_no": None,
					"picked_qty": 2,
				}
			),
			frappe._dict(
				{
					"item_code": "_Test Item 2",
					"qty": 3,
					"uom": "Nos",
					"warehouse": "_Test Warehouse",
					"batch_no": "BATCH-001",
					"serial_no": None,
					"picked_qty": 3,
				}
			),
		]

		# Mock a blank Stock Entry
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.company = "_Test Company"
		stock_entry.stock_entry_type = "Material Transfer"

		# Patch `update_common_item_properties` to track if it runs
		called_items = []

		def mock_update_common_item_properties(item, location):
			called_items.append(location.item_code)
			item.item_code = location.item_code
			item.qty = location.picked_qty
			item.uom = location.uom
			item.s_warehouse = location.warehouse

		# Replace real function with mock
		import erpnext.stock.doctype.pick_list.pick_list as pl_module

		pl_module.update_common_item_properties = mock_update_common_item_properties

		# Run the function
		updated_entry = update_stock_entry_items_with_no_reference(pick_list, stock_entry)

		# Validate the result
		self.assertEqual(len(updated_entry.items), 2)
		self.assertEqual(updated_entry.items[0].item_code, "_Test Item")
		self.assertEqual(updated_entry.items[1].item_code, "_Test Item 2")
		self.assertListEqual(called_items, ["_Test Item", "_Test Item 2"])

	def test_update_stock_entry_based_on_work_order_TC_SCK_463(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.stock.doctype.pick_list.pick_list import update_stock_entry_based_on_work_order
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		# Setup item and BOM
		item_code = make_item(
			"_Test FG Item WO", {"is_stock_item": 1, "stock_uom": "Nos", "valuation_rate": 100}
		).name

		raw_item = make_item(
			"_Test Raw Item WO", {"is_stock_item": 1, "stock_uom": "Nos", "valuation_rate": 50}
		).name
		# Create required warehouses
		wip_w = create_warehouse("_Test WIP Warehouse", {"is_group": "0"}, "_Test Company")
		fg_w = create_warehouse("_Test FG Warehouse", {"company": "_Test Company"})
		t_w = create_warehouse("_Test Warehouse", {"company": "_Test Company"})  # used in Pick List locations

		bom = make_bom(item=item_code, raw_materials=[raw_item])

		# Create Work Order
		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": item_code,
				"qty": 5,
				"fg_warehouse": fg_w,
				"wip_warehouse": wip_w,
				"bom_no": bom.name,
				"company": "_Test Company",
				"use_multi_level_bom": 0,
			}
		)
		work_order.insert()
		work_order.submit()

		# Create dummy Pick List
		pick_list = frappe.new_doc("Pick List")
		pick_list.work_order = work_order.name
		pick_list.for_qty = 5
		pick_list.locations = [
			frappe._dict(
				{
					"item_code": raw_item,
					"picked_qty": 2,
					"uom": "Nos",
					"warehouse": t_w,
				}
			)
		]

		# Mock Stock Entry
		stock_entry = frappe.new_doc("Stock Entry")

		# Patch update_common_item_properties to simulate field assignment
		called_items = []

		def mock_update_common_item_properties(item, location):
			called_items.append(location.item_code)
			item.item_code = location.item_code
			item.qty = location.picked_qty
			item.uom = location.uom
			item.s_warehouse = location.warehouse

		import erpnext.stock.doctype.pick_list.pick_list as pl_module

		pl_module.update_common_item_properties = mock_update_common_item_properties

		# Run function
		updated_entry = update_stock_entry_based_on_work_order(pick_list, stock_entry)

		# Assertions
		self.assertEqual(updated_entry.work_order, work_order.name)
		self.assertEqual(updated_entry.company, work_order.company)
		self.assertEqual(updated_entry.bom_no, bom.name)
		self.assertEqual(updated_entry.fg_completed_qty, 5)
		self.assertEqual(updated_entry.to_warehouse, work_order.wip_warehouse)
		self.assertEqual(updated_entry.items[0].item_code, raw_item)
		self.assertEqual(updated_entry.items[0].t_warehouse, work_order.wip_warehouse)
		self.assertIn(raw_item, called_items)

	def test_get_item_details_TC_SCK_464(self):
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.pick_list.pick_list import get_item_details

		# Setup
		item_code = "_Test Item UOM"
		uom = "Box"

		if not frappe.db.exists("UOM", uom):
			create_uom(uom)

		# Create Item
		item = make_item(item_code, {"stock_uom": "Nos", "is_stock_item": 1})

		# Add UOM Conversion
		if not frappe.db.exists("UOM Conversion Detail", {"uom": uom, "parent": item.name}):
			item.append("uoms", {"uom": uom, "conversion_factor": 10})
			item.save()

		# Case 1: Without passing UOM
		result = get_item_details(item_code)
		self.assertEqual(result.name, item_code)
		self.assertEqual(result.uom, "Nos")

		# Case 2: With valid UOM
		result_with_uom = get_item_details(item_code, uom=uom)
		self.assertEqual(result_with_uom.uom, uom)
		self.assertIn("conversion_factor", result_with_uom)
		self.assertEqual(result_with_uom.conversion_factor, 10)

	def test_update_picked_item_from_current_pick_list_TC_SCK_465(self):
		from frappe.utils import nowdate

		# Setup dummy Pick List with 2 locations
		pick_list = frappe.new_doc("Pick List")
		pick_list.customer = "_Test Customer"
		pick_list.company = "_Test Company"
		pick_list.purpose = "Delivery"
		pick_list.set_posting_time = 1
		pick_list.posting_date = nowdate()

		pick_list.append(
			"locations",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse",
				"picked_qty": 2,
				"stock_qty": 2,
				"batch_no": None,
				"serial_no": "SN001\nSN002",
			},
		)
		pick_list.append(
			"locations",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse",
				"picked_qty": 3,
				"stock_qty": 3,
				"batch_no": "BATCH-001",
				"serial_no": "",
			},
		)

		# Target structure to update
		picked_items = {}

		# Call method
		pick_list.update_picked_item_from_current_pick_list(picked_items)

		# Assertions
		self.assertIn("_Test Item", picked_items)

		# For serial-tracked row
		serial_key = "_Test Warehouse"
		self.assertEqual(picked_items["_Test Item"][serial_key]["picked_qty"], 2)
		self.assertListEqual(picked_items["_Test Item"][serial_key]["serial_no"], ["SN001", "SN002"])

		# For batch-tracked row
		batch_key = ("_Test Warehouse", "BATCH-001")
		self.assertEqual(picked_items["_Test Item"][batch_key]["picked_qty"], 3)
		self.assertEqual(picked_items["_Test Item"][batch_key]["batch_no"], "BATCH-001")

	def test_multiple_pick_lists_delivery_note(self):
		from erpnext.stock.doctype.pick_list.pick_list import create_dn_for_pick_lists

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"

		stock_entry = make_stock_entry(item=item_code, to_warehouse=warehouse, qty=500, basic_rate=100)

		def create_pick_list(qty):
			pick_list = frappe.get_doc(
				{
					"doctype": "Pick List",
					"company": "_Test Company",
					"customer": "_Test Customer",
					"purpose": "Delivery",
					"locations": [
						{
							"item_code": item_code,
							"warehouse": warehouse,
							"qty": qty,
							"stock_qty": qty,
							"picked_qty": 0,
							"sales_order": sales_order.name,
							"sales_order_item": sales_order.items[0].name,
						},
					],
				}
			)
			pick_list.submit()
			return pick_list

		sales_order = make_sales_order(item_code=item_code, qty=50, rate=100)
		pick_list_1 = create_pick_list(10)
		pick_list_2 = create_pick_list(20)

		delivery_note = create_dn_for_pick_lists(pick_list_1.name)
		delivery_note = create_dn_for_pick_lists(pick_list_2.name, delivery_note)
		delivery_note.items[0].qty = 5
		delivery_note.submit()

		sales_order.reload()
		pick_list_1.reload()
		pick_list_2.reload()

		self.assertEqual(sales_order.items[0].picked_qty, 30)
		self.assertEqual(pick_list_1.locations[0].delivered_qty, delivery_note.items[0].qty)
		self.assertEqual(pick_list_1.status, "Partly Delivered")
		self.assertEqual(pick_list_2.status, "Completed")

		pick_list_1.cancel()
		pick_list_2.cancel()
		delivery_note.cancel()
		sales_order.reload()
		sales_order.cancel()
		stock_entry.cancel()

	def test_packed_item_in_pick_list(self):
		warehouse_1 = "RJ Warehouse - _TC"
		warehouse_2 = "_Test Warehouse 2 - _TC"
		item_1 = make_item(properties={"is_stock_item": 0}).name
		item_2 = make_item().name
		item_3 = make_item().name

		make_product_bundle(item_1, items=[item_2, item_3])

		stock_entry_1 = make_stock_entry(item=item_2, to_warehouse=warehouse_1, qty=10, basic_rate=100)
		stock_entry_2 = make_stock_entry(item=item_3, to_warehouse=warehouse_1, qty=4, basic_rate=100)
		stock_entry_3 = make_stock_entry(item=item_3, to_warehouse=warehouse_2, qty=6, basic_rate=100)

		sales_order = make_sales_order(item_code=item_1, qty=10, rate=100)

		pick_list = create_pick_list(sales_order.name)
		pick_list.submit()
		self.assertEqual(len(pick_list.locations), 3)
		delivery_note = create_delivery_note(pick_list.name)

		self.assertEqual(delivery_note.items[0].qty, 10)
		self.assertEqual(delivery_note.packed_items[0].warehouse, warehouse_1)
		self.assertEqual(delivery_note.packed_items[1].warehouse, warehouse_2)

		pick_list.cancel()
		sales_order.cancel()
		stock_entry_1.cancel()
		stock_entry_2.cancel()
		stock_entry_3.cancel()

	def test_packed_item_multiple_times_in_so(self):
		frappe.db.delete("Item Price")
		warehouse_1 = "RJ Warehouse - _TC"
		warehouse_2 = "_Test Warehouse 2 - _TC"
		warehouse = "_Test Warehouse - _TC"
		item_1 = make_item(properties={"is_stock_item": 0}).name
		item_2 = make_item().name
		item_3 = make_item().name

		make_product_bundle(item_1, items=[item_2, item_3])

		stock_entry_1 = make_stock_entry(item=item_2, to_warehouse=warehouse_1, qty=20, basic_rate=100)
		stock_entry_2 = make_stock_entry(item=item_3, to_warehouse=warehouse_1, qty=8, basic_rate=100)
		stock_entry_3 = make_stock_entry(item=item_3, to_warehouse=warehouse_2, qty=12, basic_rate=100)

		sales_order = make_sales_order(
			item_list=[
				{"item_code": item_1, "qty": 8, "rate": 100, "warehouse": warehouse},
				{"item_code": item_1, "qty": 12, "rate": 100, "warehouse": warehouse},
			]
		)

		pick_list = create_pick_list(sales_order.name)
		pick_list.submit()
		self.assertEqual(len(pick_list.locations), 4)
		delivery_note = create_delivery_note(pick_list.name)

		self.assertEqual(delivery_note.items[0].qty, 8)
		self.assertEqual(delivery_note.items[1].qty, 12)

		self.assertEqual(delivery_note.packed_items[0].qty, 8)
		self.assertEqual(delivery_note.packed_items[2].qty, 12)

		self.assertEqual(delivery_note.packed_items[0].warehouse, warehouse_1)
		self.assertEqual(delivery_note.packed_items[1].warehouse, warehouse_1)
		self.assertEqual(delivery_note.packed_items[2].warehouse, warehouse_1)
		self.assertEqual(delivery_note.packed_items[3].warehouse, warehouse_2)

		pick_list.cancel()
		sales_order.cancel()
		stock_entry_1.cancel()
		stock_entry_2.cancel()
		stock_entry_3.cancel()

	def test_pick_list_with_and_without_so(self):
		warehouse = "_Test Warehouse - _TC"
		item = make_item().name

		sales_order = make_sales_order(item_code=item, qty=20, rate=100)
		stock_entry = make_stock_entry(item=item, to_warehouse=warehouse, qty=500, basic_rate=100)

		pick_list = create_pick_list(sales_order.name)
		pick_list.append(
			"locations",
			{
				"item_code": item,
				"qty": 10,
				"stock_qty": 10,
				"warehouse": warehouse,
				"picked_qty": 0,
			},
		)
		pick_list.submit()

		delivery_note = create_dn_for_pick_lists(pick_list.name)

		self.assertEqual(delivery_note.items[0].against_pick_list, pick_list.name)
		self.assertEqual(delivery_note.items[0].against_sales_order, sales_order.name)
		self.assertEqual(delivery_note.items[0].qty, 20)

		self.assertEqual(delivery_note.items[1].against_pick_list, pick_list.name)
		self.assertEqual(delivery_note.items[1].qty, 10)

		pick_list.cancel()
		sales_order.cancel()
		stock_entry.cancel()


def stock_check(self, voucher, qty):
	stock_entries = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_no": voucher, "warehouse": "Stores - _TC"},
		fields=["actual_qty"],
	)
	self.assertEqual(sum([entry.actual_qty for entry in stock_entries]), qty)


def validate_gl_entries(self, voucher_no, amount):
	debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
	sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
	gl_entries = frappe.get_all(
		"GL Entry", filters={"voucher_no": voucher_no}, fields=["account", "debit", "credit"]
	)

	gl_debits = {entry.account: entry.debit for entry in gl_entries}
	gl_credits = {entry.account: entry.credit for entry in gl_entries}

	self.assertAlmostEqual(gl_debits[debtor_account], amount)
	self.assertAlmostEqual(gl_credits[sales_account], amount)
