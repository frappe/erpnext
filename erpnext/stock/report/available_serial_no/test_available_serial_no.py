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

	def test_item_without_serial_nos_lists_nothing(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=2, basic_rate=100)
		make_purchase_receipt(qty=1, item_code="_Test Item with Serial No")

		filters = self.filters.copy()
		filters.update(item_code=item, from_date=add_days(today(), -1), to_date=today())
		data = frappe.get_doc("Report", "Available Serial No").get_data(filters=filters)[1]

		self.assertEqual(data, [])

	def test_opening_stock_on_from_date_is_in_the_balance(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "AVO-.#####"}
		).name
		opening_serials = [
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": f"AVO-OPEN-{frappe.generate_hash(length=6)}",
					"item_code": item,
					"company": "_Test Company",
				}
			)
			.insert()
			.name
			for _serial in range(5)
		]
		create_stock_reconciliation(
			item_code=item,
			warehouse="_Test Warehouse - _TC",
			qty=5,
			rate=100,
			serial_no=opening_serials,
			posting_date=today(),
			posting_time="00:00:00",
			purpose="Opening Stock",
		)
		make_stock_entry(
			item_code=item,
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=100,
			posting_date=today(),
			posting_time="11:00:00",
			set_posting_time=1,
		)

		filters = self.filters.copy()
		filters.update(item_code=item, warehouse="_Test Warehouse - _TC", from_date=today(), to_date=today())
		data = frappe.get_doc("Report", "Available Serial No").get_data(filters=filters)[1]

		self.assertEqual(len(data[-1]["balance_serial_no"].split("\n")), 6)

	def test_serial_nos_of_entries_without_bundle_are_in_the_balance(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "AVL-.#####"}
		).name
		warehouse = "_Test Warehouse - _TC"
		receipt = make_stock_entry(
			item_code=item, target=warehouse, qty=2, basic_rate=100, posting_date=add_days(today(), -10)
		)
		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": receipt.name}, "name")
		serial_nos = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)
		frappe.db.set_value(
			"Stock Ledger Entry",
			sle,
			{"serial_and_batch_bundle": None, "serial_no": "\n".join(serial_nos)},
			update_modified=False,
		)
		make_stock_entry(item_code=item, target=warehouse, qty=1, basic_rate=100)

		filters = self.filters.copy()
		filters.update(item_code=item, from_date=add_days(today(), -1), to_date=today())
		data = frappe.get_doc("Report", "Available Serial No").get_data(filters=filters)[1]

		self.assertTrue(set(serial_nos) <= set(data[-1]["balance_serial_no"].split("\n")))

	def test_legacy_serial_no_issued_with_a_legacy_entry_leaves_the_balance(self):
		self.assert_balance_after_issuing_a_legacy_serial_no(legacy_issue=True)

	def test_legacy_serial_no_issued_with_a_bundle_leaves_the_balance(self):
		self.assert_balance_after_issuing_a_legacy_serial_no(legacy_issue=False)

	def assert_balance_after_issuing_a_legacy_serial_no(self, legacy_issue):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "AVI-.#####"}
		).name
		warehouse = "_Test Warehouse - _TC"
		receipt = make_stock_entry(
			item_code=item, target=warehouse, qty=3, basic_rate=100, posting_date=add_days(today(), -10)
		)
		serial_nos = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)
		self.move_serial_nos_to_the_ledger_entry(receipt, serial_nos)

		issue = make_stock_entry(
			item_code=item,
			source=warehouse,
			qty=1,
			serial_no=serial_nos[:1],
			posting_date=add_days(today(), -5),
		)
		if legacy_issue:
			self.move_serial_nos_to_the_ledger_entry(issue, serial_nos[:1])

		new_receipt = make_stock_entry(item_code=item, target=warehouse, qty=1, basic_rate=100)
		new_serial_nos = get_serial_nos_from_bundle(new_receipt.items[0].serial_and_batch_bundle)

		filters = self.filters.copy()
		filters.update(item_code=item, from_date=add_days(today(), -1), to_date=today())
		data = frappe.get_doc("Report", "Available Serial No").get_data(filters=filters)[1]

		self.assertEqual(
			sorted(data[-1]["balance_serial_no"].split("\n")), sorted(serial_nos[1:] + new_serial_nos)
		)

	def move_serial_nos_to_the_ledger_entry(self, entry, serial_nos):
		frappe.db.set_value(
			"Stock Ledger Entry",
			{"voucher_no": entry.name},
			{"serial_and_batch_bundle": None, "serial_no": "\n".join(serial_nos)},
			update_modified=False,
		)
