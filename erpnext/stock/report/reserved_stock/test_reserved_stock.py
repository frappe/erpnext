# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from random import randint

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.desk.query_report import get_report_doc
from frappe.utils.data import today

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.stock_reservation_entry.test_stock_reservation_entry import (
	create_items,
	create_material_receipt,
)
from erpnext.stock.report.reserved_stock.reserved_stock import get_data as reserved_stock_report
from erpnext.tests.utils import ERPNextTestSuite


class TestReservedStock(ERPNextTestSuite):
	def setUp(self) -> None:
		super().setUp()
		self.stock_qty = 100
		self.warehouse = "_Test Warehouse - _TC"

	def test_report_access_for_operational_roles(self):
		frappe.reload_doc("stock", "report", "reserved_stock", force=True)
		for role in (
			"Stock User",
			"Stock Manager",
			"Sales User",
			"Sales Manager",
			"Purchase User",
			"Purchase Manager",
			"Accounts User",
		):
			with self.subTest(role=role):
				user = create_user(f"reserved-stock-{frappe.scrub(role)}@example.com", role)
				with self.set_user(user.name):
					if role == "Accounts User":
						self.assertRaises(frappe.PermissionError, get_report_doc, "Reserved Stock")
					else:
						self.assertTrue(frappe.has_permission("Stock Reservation Entry", "report"))
						self.assertEqual(get_report_doc("Reserved Stock").name, "Reserved Stock")
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, get_report_doc, "Reserved Stock")

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_reserved_stock_report(self):
		items_details = create_items()
		create_material_receipt(items_details, self.warehouse, qty=self.stock_qty)

		for item_code, properties in items_details.items():
			so = make_sales_order(
				item_code=item_code, qty=randint(11, 100), warehouse=self.warehouse, uom=properties.stock_uom
			)
			so.create_stock_reservation_entries()

		data = reserved_stock_report(
			filters={
				"company": so.company,
				"from_date": today(),
				"to_date": today(),
			}
		)
		self.assertEqual(len(data), len(items_details))
