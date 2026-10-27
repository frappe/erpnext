# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSerialAndBatchSummary(FrappeTestCase):
	def test_serial_filter_needs_voucher_and_item_read(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_serial_nos
		from erpnext.tests.permission_test_utils import (
			OTHER_COMPANY,
			as_user,
			make_company_fenced_user,
			make_fenced_user,
		)

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=2, basic_rate=100)
		voucher_filters = {"voucher_type": "Stock Entry", "voucher_no": [se.name]}
		expected = get_serial_nos("Serial No", "", "name", 0, 10, voucher_filters)
		self.assertEqual(len(expected), 2)

		self.assertEqual(get_serial_nos("Serial No", "", "name", 0, 10, {"voucher_no": [se.name]}), [])

		with as_user(make_company_fenced_user("summary-stock-user@example.com", ["Stock User"], se.company)):
			self.assertEqual(get_serial_nos("Serial No", "", "name", 0, 10, voucher_filters), expected)

		outsider = make_fenced_user("summary-outsider@example.com", [])
		with as_user(outsider):
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, voucher_filters
			)
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, {"item_code": item}
			)

		fenced = make_company_fenced_user("summary-fenced@example.com", ["Stock User"], OTHER_COMPANY)
		with as_user(fenced):
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, voucher_filters
			)
