# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.tests.utils import ERPNextTestSuite


class TestAvailableBatchReport(ERPNextTestSuite):
	def make_batch_with_stock(self, item, expiry_date=None):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"item": item,
				"batch_id": frappe.generate_hash(length=10),
				"expiry_date": expiry_date,
			}
		).insert()
		make_stock_entry(
			item_code=item,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=10,
			batch_no=batch.name,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -10),
		)
		return batch.name

	def test_expired_batches_are_left_out_for_a_past_date(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.available_batch_report.available_batch_report import execute

		item = make_item(properties={"has_batch_no": 1, "is_stock_item": 1}).name
		self.make_batch_with_stock(item, add_days(today(), -3))
		valid = self.make_batch_with_stock(item, add_days(today(), 30))

		data = execute(frappe._dict(to_date=add_days(today(), -1), item_code=item))[1]

		self.assertEqual([row.batch_no for row in data], [valid])

	def test_batch_issued_after_today_is_listed_for_today(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.available_batch_report.available_batch_report import execute

		item = make_item(properties={"has_batch_no": 1, "is_stock_item": 1}).name
		batch = self.make_batch_with_stock(item)
		make_stock_entry(
			item_code=item,
			source="_Test Warehouse - _TC",
			qty=5,
			batch_no=batch,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), 3),
		)

		data = execute(frappe._dict(to_date=today(), item_code=item))[1]

		self.assertEqual([(row.batch_no, row.balance_qty) for row in data], [(batch, 5)])
