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
						"qty": 5,
						"serial_no": "123450\n123451\n123452\n123453\n123454",
					}
				],
			}
		)

		try:
			stock_reconciliation.submit()
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
						"item_code": "_Test Serialized Item",
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
		self.assertEqual(pick_list.locations[0].item_code, "_Test Serialized Item")
		self.assertEqual(pick_list.locations[0].warehouse, "_Test Warehouse - _TC")
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(pick_list.locations[0].serial_no, "123450\n123451\n123452\n123453\n123454")

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
		oldest_batch_no = pr1.items[0].batch_no

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
		oldest_batch_no = pr1.items[0].batch_no
		oldest_serial_nos = pr1.items[0].serial_no

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

		self.assertEqual(pick_list.locations[0].batch_no, oldest_batch_no)
		self.assertEqual(pick_list.locations[0].serial_no, oldest_serial_nos)

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

		self.assertEqual(pick_list.locations[0].qty, delivery_note.items[0].qty)
		self.assertEqual(pick_list.locations[1].qty, delivery_note.items[1].qty)
		self.assertEqual(
			sales_order.items[0].conversion_factor, delivery_note.items[0].conversion_factor
		)

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
		for expected_item, created_item in zip(expected_items, pl.locations):
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
		for dn in frappe.get_all(
			"Delivery Note", filters={"pick_list": pick_list_1.name}, fields={"name"}
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

	def test_picklist_with_bundles(self):
		warehouse = "_Test Warehouse - _TC"

		quantities = [5, 2]
		bundle, components = create_product_bundle(quantities, warehouse=warehouse)
		bundle_items = dict(zip(components, quantities))

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
