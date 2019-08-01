# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
# test_dependencies = ['Item', 'Sales Invoice', 'Stock Entry', 'Batch']

from erpnext.selling.doctype.sales_order.sales_order import make_pick_ticket

class TestPickTicket(unittest.TestCase):
	def test_pick_ticket_picks_warehouse_for_each_item(self):
		pick_ticket = frappe.get_doc({
			'doctype': 'Pick Ticket',
			'company': '_Test Company',
			'reference_items': [{
				'item': '_Test Item Home Desktop 100',
				'reference_doctype': 'Sales Order',
				'qty': 5,
				'reference_name': '_T-Sales Order-1',
			}],
		})

		pick_ticket.set_item_locations()

		self.assertEqual(pick_ticket.items_locations[0].item, '_Test Item Home Desktop 100')
		self.assertEqual(pick_ticket.items_locations[0].warehouse, '_Test Warehouse - _TC')
		self.assertEqual(pick_ticket.items_locations[0].qty, 5)

	def test_pick_ticket_skips_out_of_stock_item(self):
		pick_ticket = frappe.get_doc({
			'doctype': 'Pick Ticket',
			'company': '_Test Company',
			'reference_items': [{
				'item': '_Test Item Warehouse Group Wise Reorder',
				'reference_doctype': 'Sales Order',
				'qty': 1000,
				'reference_name': '_T-Sales Order-1',
			}],
		})

		pick_ticket.set_item_locations()

		self.assertEqual(pick_ticket.items_locations[0].item, '_Test Item Warehouse Group Wise Reorder')
		self.assertEqual(pick_ticket.items_locations[0].warehouse, '_Test Warehouse Group-C1 - _TC')
		self.assertEqual(pick_ticket.items_locations[0].qty, 30)


	def test_pick_ticket_skips_items_in_expired_batch(self):
		pass

	def test_pick_ticket_shows_serial_no_for_serialized_item(self):

		stock_reconciliation = frappe.get_doc({
			'doctype': 'Stock Reconciliation',
			'company': '_Test Company',
			'items': [{
				'item_code': '_Test Serialized Item',
				'warehouse': '_Test Warehouse - _TC',
				'qty': 5,
				'serial_no': '123450\n123451\n123452\n123453\n123454'
			}]
		})

		stock_reconciliation.submit()

		pick_ticket = frappe.get_doc({
			'doctype': 'Pick Ticket',
			'company': '_Test Company',
			'reference_items': [{
				'item': '_Test Serialized Item',
				'reference_doctype': 'Sales Order',
				'qty': 1000,
				'reference_name': '_T-Sales Order-1',
			}],
		})

		pick_ticket.set_item_locations()
		self.assertEqual(pick_ticket.items_locations[0].item, '_Test Serialized Item')
		self.assertEqual(pick_ticket.items_locations[0].warehouse, '_Test Warehouse Group-C1 - _TC')
		self.assertEqual(pick_ticket.items_locations[0].qty, 30)
		self.assertEqual(pick_ticket.items_locations[0].serial_no, 30)


	def test_pick_ticket_for_multiple_reference_doctypes(self):
		pass


## records required

'''
batch no
items
sales invoice
stock entries
	bin
	stock ledger entry
warehouses
'''