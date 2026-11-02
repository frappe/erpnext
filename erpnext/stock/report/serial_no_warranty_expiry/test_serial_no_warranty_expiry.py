# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import os

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSerialNoWarrantyExpiry(ERPNextTestSuite):
	def get_report_spec(self):
		path = os.path.join(os.path.dirname(__file__), "serial_no_warranty_expiry.json")
		return json.loads(json.load(open(path))["json"])

	def test_report_shows_the_warranty_expiry_date(self):
		spec = self.get_report_spec()

		self.assertIn(["warranty_expiry_date", "Serial No"], spec["fields"])
		self.assertEqual(spec["order_by"], "`tabSerial No`.`warranty_expiry_date` asc")

	def test_consumed_serial_nos_are_not_listed(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SNW-.#####",
				"warranty_period": 30,
			}
		).name
		receipt = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=2, rate=100)
		serial_nos = frappe.get_all(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, pluck="serial_no"
		)
		create_delivery_note(
			item_code=item,
			qty=1,
			serial_no=frappe.db.get_value("Serial No", serial_nos[0], "serial_no"),
			use_serial_batch_fields=1,
			warehouse="Stores - _TC",
		)
		make_stock_entry(
			item_code=item,
			from_warehouse="Stores - _TC",
			qty=1,
			serial_no=frappe.db.get_value("Serial No", serial_nos[1], "serial_no"),
			use_serial_batch_fields=1,
		)

		listed = frappe.get_all(
			"Serial No",
			filters=self.get_report_spec()["filters"] + [["Serial No", "item_code", "=", item]],
			pluck="name",
		)

		self.assertEqual(listed, [serial_nos[0]])
