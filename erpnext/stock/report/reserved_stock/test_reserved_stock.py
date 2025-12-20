# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from random import randint

from frappe.tests import IntegrationTestCase
from frappe.utils.data import today

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.stock_reservation_entry.test_stock_reservation_entry import (
	cancel_all_stock_reservation_entries,
	create_items,
	create_material_receipt,
)
from erpnext.stock.report.reserved_stock.reserved_stock import get_data as reserved_stock_report


class TestReservedStock(IntegrationTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.stock_qty = 100
		self.warehouse = "_Test Warehouse - _TC"

	def tearDown(self) -> None:
		cancel_all_stock_reservation_entries()
		return super().tearDown()

	@IntegrationTestCase.change_settings(
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
