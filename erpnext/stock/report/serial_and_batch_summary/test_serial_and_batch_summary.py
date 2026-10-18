# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSerialAndBatchSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		return execute(frappe._dict(extra))[1]

	def test_serial_receipt_listed(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=3, basic_rate=100)

		data = self.run_report(voucher_no=[se.name], voucher_type="Stock Entry")

		self.assertEqual(len(data), 3)
		self.assertEqual(len({row.serial_no for row in data}), 3)
		for row in data:
			self.assertTrue(row.serial_no)
			self.assertEqual(
				row.serial_no_number, frappe.db.get_value("Serial No", row.serial_no, "serial_no")
			)
			self.assertEqual(row.qty, 1)
			self.assertEqual(row.incoming_rate, 100)
			self.assertEqual(row.warehouse, "Stores - _TC")
			self.assertEqual(row.voucher_no, se.name)

	def test_batch_filter_shows_numbers_to_a_select_only_role(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_batch_nos

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(doctype="Batch", item=item, batch_id="Summary-Filter-Batch").insert()
		user = "summary-sales-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				doctype="User",
				email=user,
				first_name="Summary",
				send_welcome_email=0,
				roles=[{"role": "Sales User"}],
			).insert()

		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Batch", "read"))
			rows = get_batch_nos("Batch", "Summary-Filter", "name", 0, 5, {"item_code": item})

		self.assertEqual([tuple(row) for row in rows], [(batch.name, "Summary-Filter-Batch", item)])

	def test_filters_list_nothing_without_item_or_voucher(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_batch_nos

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		frappe.get_doc(doctype="Batch", item=item, batch_id="Summary-Unscoped-Batch").insert()

		self.assertEqual(get_batch_nos("Batch", "Summary-Unscoped", "name", 0, 5, {}), [])

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

	def test_batch_receipt_listed(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SBB-.#####",
			}
		).name
		se = make_stock_entry(item_code=item, to_warehouse="_Test Warehouse - _TC", qty=10, basic_rate=50)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		data = self.run_report(voucher_no=[se.name], voucher_type="Stock Entry")

		row = next((d for d in data if d.batch_no == batch_no), None)
		self.assertIsNotNone(row)
		self.assertEqual(row.batch_no_number, frappe.db.get_value("Batch", batch_no, "batch_id"))
		self.assertEqual(row.qty, 10)
		self.assertEqual(row.incoming_rate, 50)
		self.assertEqual(row.warehouse, "_Test Warehouse - _TC")
		self.assertEqual(row.voucher_no, se.name)

	def test_group_warehouse_includes_its_warehouses(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=2, basic_rate=100)
		group = frappe.db.get_value("Warehouse", "Stores - _TC", "parent_warehouse")

		columns, data = execute(
			frappe._dict(voucher_no=[se.name], voucher_type="Stock Entry", warehouse=group)
		)[:2]

		self.assertEqual(len(data), 2)
		self.assertIn("warehouse", [column.get("fieldname") for column in columns])
		self.assertEqual({row.warehouse for row in data}, {"Stores - _TC"})

	def test_qty_column_is_shown_for_serial_items(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=1, basic_rate=100)

		columns = execute(frappe._dict(item_code=item, voucher_no=[se.name], voucher_type="Stock Entry"))[0]

		self.assertIn("qty", [column.get("fieldname") for column in columns])

	def test_batch_filter_lists_nothing_without_access_to_batches(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_batch_nos

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		frappe.get_doc(doctype="Batch", item=item, batch_id="Summary-Hidden-Batch").insert()
		user = "summary-purchase-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				doctype="User",
				email=user,
				first_name="Summary",
				send_welcome_email=0,
				roles=[{"role": "Purchase User"}],
			).insert()

		with self.set_user(user):
			rows = get_batch_nos("Batch", "Summary-Hidden", "name", 0, 5, {"item_code": item})

		self.assertEqual(rows, [])
