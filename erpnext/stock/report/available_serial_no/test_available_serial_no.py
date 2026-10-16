# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestStockLedgerReeport(ERPNextTestSuite):
	def setUp(self) -> None:
		item = create_item("_Test Item with Serial No", is_stock_item=1)
		item.has_serial_no = 1
		item.serial_no_series = "TEST.###"
		item.save(ignore_permissions=True)

		self.filters = frappe._dict(
			company="_Test Company",
			from_date=today(),
			to_date=add_days(today(), 30),
			item_code="_Test Item with Serial No",
		)

	def test_available_serial_no(self):
		report = frappe.get_doc("Report", "Available Serial No")

		make_purchase_receipt(qty=10, item_code="_Test Item with Serial No")
		data = report.get_data(filters=self.filters)
		serial_nos = [item for item in data[-1][-1]["balance_serial_no"].split("\n")]

		# Test 1: Since we have created an inward entry with Purchase Receipt of 10 qty, we should have 10 serial nos
		self.assertEqual(len(serial_nos), 10)

		create_delivery_note(qty=5, item_code="_Test Item with Serial No")
		data = report.get_data(filters=self.filters)
		serial_nos = [item for item in data[-1][-1]["balance_serial_no"].split("\n")]

		# Test 2: Since we have created a delivery note of 5 qty, we should have 5 serial nos
		self.assertEqual(len(serial_nos), 5)

	def test_balance_serial_nos_include_stock_before_from_date(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "AVS-.#####"}
		).name
		warehouse = "_Test Warehouse - _TC"
		for qty, days in ((3, -10), (2, -8)):
			make_stock_entry(
				item_code=item,
				target=warehouse,
				qty=qty,
				basic_rate=100,
				posting_date=add_days(today(), days),
			)
		make_stock_entry(item_code=item, source=warehouse, qty=1, posting_date=add_days(today(), -5))

		filters = self.filters.copy()
		filters.update(item_code=item, from_date=add_days(today(), -7), to_date=today())
		data = frappe.get_doc("Report", "Available Serial No").get_data(filters=filters)[1]

		in_stock = frappe.get_all(
			"Serial No", filters={"item_code": item, "warehouse": warehouse}, pluck="name"
		)
		self.assertEqual(len(in_stock), 4)
		self.assertEqual(sorted(data[-1]["balance_serial_no"].split("\n")), sorted(in_stock))
