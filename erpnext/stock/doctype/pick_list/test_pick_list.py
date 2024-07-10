# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _dict
from frappe.tests.utils import FrappeTestCase

from erpnext.selling.doctype.sales_order.sales_order import create_pick_list
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.packed_item.test_packed_item import create_product_bundle
from erpnext.stock.doctype.pick_list.pick_list import create_delivery_note
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
		item_code = make_item().name
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
						"conversion_factor": 5,
						"stock_qty": 5,
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

		self.assertEqual(pick_list.locations[0].qty, delivery_note.items[0].qty)
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
				"picker": "P001",
				"locations": [
					{
						"item_code": "_Test Item ",
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
			filters={"pick_list": pick_list.name, "customer": "_Test Customer"},
			fields={"name"},
		):
			for dn_item in frappe.get_doc("Delivery Note", dn.name).get("items"):
				self.assertEqual(dn_item.item_code, "_Test Item")
				self.assertEqual(dn_item.against_sales_order, sales_order_1.name)
				self.assertEqual(dn_item.pick_list_item, pick_list.locations[dn_item.idx - 1].name)

		for dn in frappe.get_all(
			"Delivery Note",
			filters={"pick_list": pick_list.name, "customer": "_Test Customer 1"},
			fields={"name"},
		):
			for dn_item in frappe.get_doc("Delivery Note", dn.name).get("items"):
				self.assertEqual(dn_item.item_code, "_Test Item 2")
				self.assertEqual(dn_item.against_sales_order, sales_order_2.name)
		# test DN creation without so
		pick_list_1 = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": "_Test Company",
				"purpose": "Delivery",
				"picker": "P001",
				"locations": [
					{
						"item_code": "_Test Item ",
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
		for dn in frappe.get_all("Delivery Note", filters={"pick_list": pick_list_1.name}, fields={"name"}):
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
