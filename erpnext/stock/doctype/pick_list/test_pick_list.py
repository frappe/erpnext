# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
test_dependencies = ['Item', 'Sales Invoice', 'Stock Entry', 'Batch']

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
					'item_code': '_Test Item Home Desktop 100',
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
			'locations': [{
				'item_code': '_Test Item Home Desktop 100',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, '_Test Item Home Desktop 100')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)

	def test_pick_list_splits_row_according_to_warhouse_availability(self):
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

		stock_reconciliation.submit()

		pick_list = frappe.get_doc({
			'doctype': 'Pick List',
			'company': '_Test Company',
			'customer': '_Test Customer',
			'items_based_on': 'Sales Order',
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

	def test_pick_list_for_items_from_multiple_sales_orders(self):
		try:
			frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'company': '_Test Company',
				'purpose': 'Opening Stock',
				'expense_account': 'Temporary Opening - _TC',
				'items': [{
					'item_code': '_Test Item Home Desktop 100',
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
					'item_code': '_Test Item Home Desktop 100',
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
			'locations': [{
				'item_code': '_Test Item Home Desktop 100',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': '_T-Sales Order-1',
				'sales_order_item': '_T-Sales Order-1_item',
			}, {
				'item_code': '_Test Item Home Desktop 100',
				'qty': 5,
				'stock_qty': 5,
				'conversion_factor': 1,
				'sales_order': sales_order.name,
				'sales_order_item': sales_order.items[0].name,
			}]
		})
		pick_list.set_item_locations()

		self.assertEqual(pick_list.locations[0].item_code, '_Test Item Home Desktop 100')
		self.assertEqual(pick_list.locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[0].qty, 5)
		self.assertEqual(pick_list.locations[0].sales_order_item, '_T-Sales Order-1_item')

		self.assertEqual(pick_list.locations[1].item_code, '_Test Item Home Desktop 100')
		self.assertEqual(pick_list.locations[1].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_list.locations[1].qty, 5)
		self.assertEqual(pick_list.locations[1].sales_order_item, sales_order.items[0].name)


	# def test_pick_list_skips_items_in_expired_batch(self):
	# 	pass

	# def test_pick_list_from_sales_order(self):
	# 	pass

	# def test_pick_list_from_work_order(self):
	# 	pass

	# def test_pick_list_from_material_request(self):
	# 	pass