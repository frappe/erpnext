# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
test_dependencies = ['Item', 'Sales Invoice', 'Stock Entry', 'Batch']

from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.pick_list.pick_list import create_delivery_note
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation \
		import EmptyStockReconciliationItemsError

class TestPickList(unittest.TestCase):

	def test_pick_list_picks_warehouse_for_each_item(self):
		try:
			frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'company': '_Test Company',
				'purpose': 'Opening Stock',
				'expense_account': 'Temporary Opening - _TC',
				'items': [{
					'item_code': '_Test Item',
					'warehouse': '_Test Warehouse - _TC',
					'valuation_rate': 100,
					'qty': 5
				}]
			}).submit()
		except EmptyStockReconciliationItemsError:
			pass

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
			'purpose': 'Delivery',
			'locations': [{
				'item_code': '_Test Item',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, '_Test Item')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)

	def test_pick_list_splits_row_according_to_warehouse_availability(self):
		try:
			frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'company': '_Test Company',
				'purpose': 'Opening Stock',
				'expense_account': 'Temporary Opening - _TC',
				'items': [{
					'item_code': '_Test Item Warehouse Group Wise Reorder',
					'warehouse': '_Test Warehouse Group-C1 - _TC',
					'valuation_rate': 100,
					'qty': 5
				}]
			}).submit()
		except EmptyStockReconciliationItemsError:
			pass

		try:
			frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'company': '_Test Company',
				'purpose': 'Opening Stock',
				'expense_account': 'Temporary Opening - _TC',
				'items': [{
					'item_code': '_Test Item Warehouse Group Wise Reorder',
					'warehouse': '_Test Warehouse 2 - _TC',
					'valuation_rate': 400,
					'qty': 10
				}]
			}).submit()
		except EmptyStockReconciliationItemsError:
			pass

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
			'purpose': 'Delivery',
			'locations': [{
				'item_code': '_Test Item Warehouse Group Wise Reorder',
				'qty': 1000,
				'stock_qty': 1000,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}]
		})

		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, '_Test Item Warehouse Group Wise Reorder')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse Group-C1 - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)

		self.assertEqual(pick_list.locations[1].item_code, '_Test Item Warehouse Group Wise Reorder')
		self.assertEqual(pick_list.locations[1].warehouse, '_Test Warehouse 2 - _TC')
		self.assertEqual(pick_list.locations[1].qty, 10)

	def test_pick_list_shows_serial_no_for_serialized_item(self):

		stock_reconciliation = frappe.get_doc({
			'doctype': 'Stock Reconciliation',
			'purpose': 'Stock Reconciliation',
			'company': '_Test Company',
			'items': [{
				'item_code': '_Test Serialized Item',
				'warehouse': '_Test Warehouse - _TC',
				'valuation_rate': 100,
				'qty': 5,
				'serial_no': '123450\n123451\n123452\n123453\n123454'
			}]
		})

		try:
			stock_reconciliation.submit()
		except EmptyStockReconciliationItemsError:
			pass

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
			'purpose': 'Delivery',
			'locations': [{
				'item_code': '_Test Serialized Item',
				'qty': 1000,
				'stock_qty': 1000,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}]
		})

		pick_list.set_item_locations()
		self.assertEqual(pick_list.locations[0].item_code, '_Test Serialized Item')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(pick_list.locations[0].serial_no, '123450\n123451\n123452\n123453\n123454')

	def test_pick_list_shows_batch_no_for_batched_item(self):
		# check if oldest batch no is picked
		item = frappe.db.exists("Item", {'item_name': 'Batched Item'})
		if not item:
			item = create_item("Batched Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.batch_number_series = "B-BATCH-.##"
			item.save()
		else:
			item = frappe.get_doc("Item", {'item_name': 'Batched Item'})

		pr1 = make_purchase_receipt(item_code="Batched Item", qty=1, rate=100.0)

		pr1.load_from_db()
		oldest_batch_no = pr1.items[0].batch_no

		pr2 = make_purchase_receipt(item_code="Batched Item", qty=2, rate=100.0)

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'purpose': 'Material Transfer',
			'locations': [{
				'item_code': 'Batched Item',
				'qty': 1,
				'stock_qty': 1,
				'conversion_factor': 1,
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].batch_no, oldest_batch_no)

		pr1.cancel()
		pr2.cancel()


	def test_pick_list_for_batched_and_serialised_item(self):
		# check if oldest batch no and serial nos are picked
		item = frappe.db.exists("Item", {'item_name': 'Batched and Serialised Item'})
		if not item:
			item = create_item("Batched and Serialised Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "B-BATCH-.##"
			item.serial_no_series = "S-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {'item_name': 'Batched and Serialised Item'})

		pr1 = make_purchase_receipt(item_code="Batched and Serialised Item", qty=2, rate=100.0)

		pr1.load_from_db()
		oldest_batch_no = pr1.items[0].batch_no
		oldest_serial_nos = pr1.items[0].serial_no

		pr2 = make_purchase_receipt(item_code="Batched and Serialised Item", qty=2, rate=100.0)

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'purpose': 'Material Transfer',
			'locations': [{
				'item_code': 'Batched and Serialised Item',
				'qty': 2,
				'stock_qty': 2,
				'conversion_factor': 1,
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].batch_no, oldest_batch_no)
		self.assertEqual(pick_list.locations[0].serial_no, oldest_serial_nos)

		pr1.cancel()
		pr2.cancel()

	def test_pick_list_for_items_from_multiple_sales_orders(self):
		try:
			frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'company': '_Test Company',
				'purpose': 'Opening Stock',
				'expense_account': 'Temporary Opening - _TC',
				'items': [{
					'item_code': '_Test Item',
					'warehouse': '_Test Warehouse - _TC',
					'valuation_rate': 100,
					'qty': 10
				}]
			}).submit()
		except EmptyStockReconciliationItemsError:
			pass

		sales_order = frappe.get_doc({
				'doctype': "Sales Order",
				'customer': '_Test Customer',
				'company': '_Test Company',
				'items': [{
					'item_code': '_Test Item',
					'qty': 10,
					'delivery_date': frappe.utils.today()
				}],
			})
		sales_order.submit()

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
			'purpose': 'Delivery',
			'locations': [{
				'item_code': '_Test Item',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}, {
				'item_code': '_Test Item',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': sales_order.name,
				'sales_order_item': sales_order.items[0].name,
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, '_Test Item')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(pick_list.locations[0].sales_order_item, '_T-Sales Order-1_item')

		self.assertEqual(pick_list.locations[1].item_code, '_Test Item')
		self.assertEqual(pick_list.locations[1].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[1].qty, 5)
		self.assertEqual(pick_list.locations[1].sales_order_item, sales_order.items[0].name)

	def test_pick_list_for_items_with_multiple_UOM(self):
		purchase_receipt = make_purchase_receipt(item_code="_Test Item", qty=10)
		purchase_receipt.submit()

		sales_order = frappe.get_doc({
				'doctype': 'Sales Order',
				'customer': '_Test Customer',
				'company': '_Test Company',
				'items': [{
					'item_code': '_Test Item',
					'qty': 1,
					'conversion_factor': 5,
					'delivery_date': frappe.utils.today()
				}, {
					'item_code': '_Test Item',
					'qty': 1,
					'conversion_factor': 1,
					'delivery_date': frappe.utils.today()
				}],
			}).insert()
		sales_order.submit()

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
			'purpose': 'Delivery',
			'locations': [{
				'item_code': '_Test Item',
				'qty': 1,
				'stock_qty': 5,
				'conversion_factor': 5,
				'sales_order': sales_order.name,
				'sales_order_item': sales_order.items[0].name ,
			}, {
				'item_code': '_Test Item',
				'qty': 1,
				'stock_qty': 1,
				'conversion_factor': 1,
				'sales_order': sales_order.name,
				'sales_order_item': sales_order.items[1].name ,
			}]
		})
		pick_list.set_item_locations()
		pick_list.submit()

		delivery_note = create_delivery_note(pick_list.name)

		self.assertEqual(pick_list.locations[0].qty, delivery_note.items[0].qty)
		self.assertEqual(pick_list.locations[1].qty, delivery_note.items[1].qty)
		self.assertEqual(sales_order.items[0].conversion_factor, delivery_note.items[0].conversion_factor)

		pick_list.cancel()
		sales_order.cancel()
		purchase_receipt.cancel()

	# def test_pick_list_skips_items_in_expired_batch(self):
	# 	pass

	# def test_pick_list_from_sales_order(self):
	# 	pass

	# def test_pick_list_from_work_order(self):
	# 	pass

	# def test_pick_list_from_material_request(self):
	# 	pass
