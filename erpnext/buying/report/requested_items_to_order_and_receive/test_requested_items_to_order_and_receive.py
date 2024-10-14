# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.buying.report.requested_items_to_order_and_receive.requested_items_to_order_and_receive import (
	get_data,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.material_request.material_request import make_purchase_order


class TestRequestedItemsToOrderAndReceive(IntegrationTestCase):
	def setUp(self) -> None:
		create_item("Test MR Report Item")
		self.setup_material_request()  # to order and receive
		self.setup_material_request(order=True, days=1)  # to receive (ordered)
		self.setup_material_request(order=True, receive=True, days=2)  # complete (ordered & received)

		self.filters = frappe._dict(
			company="_Test Company",
			from_date=today(),
			to_date=add_days(today(), 30),
			item_code="Test MR Report Item",
		)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_date_range(self):
		data = get_data(self.filters)
		self.assertEqual(len(data), 2)  # MRs today should be fetched

		data = get_data(self.filters.update({"from_date": add_days(today(), 10)}))
		self.assertEqual(len(data), 0)  # MRs today should not be fetched as from date is in future

	def test_ordered_received_material_requests(self):
		data = get_data(self.filters)

		# from the 3 MRs made, only 2 (to receive) should be fetched
		self.assertEqual(len(data), 2)
		self.assertEqual(data[0].ordered_qty, 0.0)
		self.assertEqual(data[1].ordered_qty, 57.0)

	def setup_material_request(self, order=False, receive=False, days=0):
		po = None
		mr = frappe.copy_doc(self.globalTestRecords["Material Request"][0])
		mr.transaction_date = add_days(today(), days)
		mr.schedule_date = add_days(mr.transaction_date, 1)
		for row in mr.items:
			row.item_code = "Test MR Report Item"
			row.item_name = "Test MR Report Item"
			row.description = "Test MR Report Item"
			row.uom = "Nos"
			row.schedule_date = mr.schedule_date
		mr.submit()

		if order or receive:
			po = make_purchase_order(mr.name)
			po.supplier = "_Test Supplier"
			po.submit()
			if receive:
				pr = make_purchase_receipt(po.name)
				pr.submit()
