# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.utils import add_days, flt, today

from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.item_standard_cost.test_item_standard_cost import (
	create_item_standard_cost,
	create_standard_cost_item,
	ensure_ppv_account,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


def make_return(doctype, source_name, qty=None):
	entry = make_return_doc(doctype, source_name)
	if qty is not None:
		entry.items[0].qty = -qty
		if doctype == "Purchase Receipt":
			entry.items[0].received_qty = -qty

	entry.submit()
	return entry


def get_return_sle(voucher_no):
	return frappe.db.get_value(
		"Stock Ledger Entry",
		{"voucher_no": voucher_no, "is_cancelled": 0},
		["stock_value_difference", "stock_queue", "serial_and_batch_bundle"],
		as_dict=True,
	)


class TestReturnValuation(ERPNextTestSuite):
	def make_item(self, valuation_method):
		return make_item(properties={"is_stock_item": 1, "valuation_method": valuation_method}).name

	def receive(self, item_code, rates, qty=10, **kwargs):
		return [
			make_purchase_receipt(item_code=item_code, warehouse=WAREHOUSE, qty=qty, rate=rate, **kwargs)
			for rate in rates
		]

	def deliver(self, item_code, qty, **kwargs):
		return create_delivery_note(item_code=item_code, warehouse=WAREHOUSE, qty=qty, rate=500, **kwargs)

	def assertReturnValued(self, entry, stock_value_difference, stock_queue=None):
		sle = get_return_sle(entry.name)
		self.assertEqual(flt(sle.stock_value_difference, 2), stock_value_difference)
		if stock_queue is not None:
			self.assertEqual(json.loads(sle.stock_queue), stock_queue)

		return sle

	def test_fifo_purchase_return_takes_receipt_rate_layer_else_oldest_layer(self):
		item_code = self.make_item("FIFO")
		receipts = self.receive(item_code, (100, 150, 200))
		make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=10)

		self.assertReturnValued(
			make_return("Purchase Receipt", receipts[2].name, 4), -800, [[10, 150], [6, 200]]
		)
		self.assertReturnValued(
			make_return("Purchase Receipt", receipts[0].name, 2), -300, [[8, 150], [6, 200]]
		)

	def test_fifo_sales_return_at_delivery_rate(self):
		item_code = self.make_item("FIFO")
		self.receive(item_code, (100, 150))
		delivery = self.deliver(item_code, 10)

		self.assertReturnValued(make_return("Delivery Note", delivery.name, 4), 400, [[10, 150], [4, 100]])

	def test_lifo_purchase_return_takes_receipt_rate_layer_else_newest_layer(self):
		item_code = self.make_item("LIFO")
		receipts = self.receive(item_code, (100, 200, 300))
		make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=10)

		self.assertReturnValued(
			make_return("Purchase Receipt", receipts[0].name, 4), -400, [[6, 100], [10, 200]]
		)
		self.assertReturnValued(
			make_return("Purchase Receipt", receipts[2].name, 3), -600, [[6, 100], [7, 200]]
		)

	def test_lifo_sales_return_at_delivery_rate(self):
		item_code = self.make_item("LIFO")
		self.receive(item_code, (100, 200), posting_date=add_days(today(), -3))
		delivery = self.deliver(item_code, 5, posting_date=add_days(today(), -2))
		self.receive(item_code, (300,), posting_date=add_days(today(), -1))

		self.assertReturnValued(
			make_return("Delivery Note", delivery.name, 2),
			400,
			[[10, 100], [5, 200], [10, 300], [2, 200]],
		)

	def test_standard_cost_returns_at_current_standard_rate(self):
		ensure_ppv_account(COMPANY)
		item_code = create_standard_cost_item().name
		create_item_standard_cost(item_code, rate=100, effective_date=add_days(today(), -10))

		receipt = make_purchase_receipt(
			item_code=item_code, warehouse=WAREHOUSE, qty=10, rate=150, posting_date=add_days(today(), -5)
		)
		delivery = self.deliver(item_code, 4, posting_date=add_days(today(), -4))
		create_item_standard_cost(item_code, rate=130, effective_date=add_days(today(), -1))

		self.assertReturnValued(make_return("Purchase Receipt", receipt.name, 2), -260)
		self.assertReturnValued(make_return("Delivery Note", delivery.name, 1), 130)

	def test_batch_sales_return_at_delivery_rate_after_batch_rate_changes(self):
		item_code = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "TRV-BATCH-.#####"}
		).name
		batch_no = (
			frappe.get_doc({"doctype": "Batch", "batch_id": f"TRV-{item_code}", "item": item_code})
			.insert()
			.name
		)
		self.assertTrue(frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"))

		batch_args = {"batch_no": batch_no, "use_serial_batch_fields": 1}
		make_purchase_receipt(item_code=item_code, warehouse=WAREHOUSE, qty=10, rate=100, **batch_args)
		delivery = self.deliver(item_code, 5, **batch_args)
		make_purchase_receipt(item_code=item_code, warehouse=WAREHOUSE, qty=10, rate=400, **batch_args)

		sle = self.assertReturnValued(make_return("Delivery Note", delivery.name), 500)
		rate = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": sle.serial_and_batch_bundle}, "incoming_rate"
		)
		self.assertEqual(flt(rate, 2), 100)
