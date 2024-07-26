# Python bytecode 2.7 (62211)
# Embedded file name: /Users/anuragmishra/frappe-develop/apps/erpnext/erpnext/buying/report/subcontracted_item_to_be_received/test_subcontracted_item_to_be_received.py
# Compiled at: 2019-05-06 09:51:46
# Decompiled by https://python-decompiler.com


import copy

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.buying.report.subcontracted_item_to_be_received.subcontracted_item_to_be_received import (
	execute,
)
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_rm_items,
	get_subcontracting_order,
	make_service_item,
	make_stock_in_entry,
	make_stock_transfer_entry,
)
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)


class TestSubcontractedItemToBeReceived(FrappeTestCase):
	def test_pending_and_received_qty(self):
		make_service_item("Subcontracted Service Item 1")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 10,
				"rate": 500,
				"fg_item": "_Test FG Item",
				"fg_item_qty": 10,
			},
		]
		sco = get_subcontracting_order(
			service_items=service_items, supplier_warehouse="_Test Warehouse 1 - _TC"
		)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		for item in rm_items:
			item["sco_rm_detail"] = sco.items[0].name

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		make_subcontracting_receipt_against_sco(sco.name)
		sco.reload()
		col, data = execute(
			filters=frappe._dict(
				{
					"order_type": "Subcontracting Order",
					"supplier": sco.supplier,
					"from_date": frappe.utils.get_datetime(
						frappe.utils.add_to_date(sco.transaction_date, days=-10)
					),
					"to_date": frappe.utils.get_datetime(
						frappe.utils.add_to_date(sco.transaction_date, days=10)
					),
				}
			)
		)
		self.assertEqual(data[0]["pending_qty"], 5)
		self.assertEqual(data[0]["received_qty"], 5)
		self.assertEqual(data[0]["subcontract_order"], sco.name)
		self.assertEqual(data[0]["supplier"], sco.supplier)


def make_subcontracting_receipt_against_sco(sco, quantity=5):
	scr = make_subcontracting_receipt(sco)
	scr.items[0].qty = quantity
	scr.insert()
	scr.submit()
