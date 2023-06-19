# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.utils import get_stock_balance


class TestStockReservationEntry(FrappeTestCase):
	def setUp(self) -> None:
		self.items = create_items()
		create_material_receipt(self.items)

	def tearDown(self) -> None:
		return super().tearDown()

	def test_validate_stock_reservation_settings(self) -> None:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			validate_stock_reservation_settings,
		)

		voucher = frappe._dict(
			{
				"doctype": "Sales Order",
			}
		)

		# Case - 1: When `Stock Reservation` is disabled in `Stock Settings`, throw `ValidationError`
		with change_settings("Stock Settings", {"enable_stock_reservation": 0}):
			self.assertRaises(frappe.ValidationError, validate_stock_reservation_settings, voucher)

		with change_settings("Stock Settings", {"enable_stock_reservation": 1}):
			# Case - 2: When `Voucher Type` is not allowed for `Stock Reservation`, throw `ValidationError`
			voucher.doctype = "NOT ALLOWED"
			self.assertRaises(frappe.ValidationError, validate_stock_reservation_settings, voucher)

			# Case - 3: When `Voucher Type` is allowed for `Stock Reservation`
			voucher.doctype = "Sales Order"
			self.assertIsNone(validate_stock_reservation_settings(voucher), None)

	def test_get_available_qty_to_reserve(self) -> None:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_available_qty_to_reserve,
		)

		item_code, warehouse = "SR Item 1", "_Test Warehouse - _TC"

		# Case - 1: When `Reserved Qty` is `0`, Available Qty to Reserve = Actual Qty
		cancel_all_stock_reservation_entries()
		available_qty_to_reserve = get_available_qty_to_reserve(item_code, warehouse)
		expected_available_qty_to_reserve = get_stock_balance(item_code, warehouse)

		self.assertEqual(available_qty_to_reserve, expected_available_qty_to_reserve)

		# Case - 2: When `Reserved Qty` is `> 0`, Available Qty to Reserve = Actual Qty - Reserved Qty
		sre = make_stock_reservation_entry(
			item_code=item_code,
			warehouse=warehouse,
			ignore_validate=True,
		)
		available_qty_to_reserve = get_available_qty_to_reserve(item_code, warehouse)
		expected_available_qty_to_reserve = get_stock_balance(item_code, warehouse) - sre.reserved_qty

		self.assertEqual(available_qty_to_reserve, expected_available_qty_to_reserve)

	def test_update_status(self) -> None:
		sre = make_stock_reservation_entry(
			reserved_qty=30,
			ignore_validate=True,
			do_not_submit=True,
		)

		# Draft: When DocStatus is `0`
		sre.load_from_db()
		self.assertEqual(sre.status, "Draft")

		# Partially Reserved: When DocStatus is `1` and `Reserved Qty` < `Voucher Qty`
		sre.submit()
		sre.load_from_db()
		self.assertEqual(sre.status, "Partially Reserved")

		# Reserved: When DocStatus is `1` and `Reserved Qty` = `Voucher Qty`
		sre.reserved_qty = sre.voucher_qty
		sre.db_update()
		sre.update_status()
		sre.load_from_db()
		self.assertEqual(sre.status, "Reserved")

		# Partially Delivered: When DocStatus is `1` and (0 < `Delivered Qty` < `Voucher Qty`)
		sre.delivered_qty = 10
		sre.db_update()
		sre.update_status()
		sre.load_from_db()
		self.assertEqual(sre.status, "Partially Delivered")

		# Delivered: When DocStatus is `1` and `Delivered Qty` = `Voucher Qty`
		sre.delivered_qty = sre.voucher_qty
		sre.db_update()
		sre.update_status()
		sre.load_from_db()
		self.assertEqual(sre.status, "Delivered")

		# Cancelled: When DocStatus is `2`
		sre.cancel()
		sre.load_from_db()
		self.assertEqual(sre.status, "Cancelled")

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_update_reserved_qty_in_voucher(self) -> None:
		item_code, warehouse = "SR Item 1", "_Test Warehouse - _TC"

		# Step - 1: Create a `Sales Order`
		so = make_sales_order(
			item_code=item_code,
			warehouse=warehouse,
			qty=50,
			rate=100,
			do_not_submit=True,
		)
		so.reserve_stock = 0  # Stock Reservation Entries won't be created on submit
		so.items[0].reserve_stock = 1
		so.save()
		so.submit()

		# Step - 2: Create a `Stock Reservation Entry[1]` for the `Sales Order Item`
		sre1 = make_stock_reservation_entry(
			item_code=item_code,
			warehouse=warehouse,
			voucher_type="Sales Order",
			voucher_no=so.name,
			voucher_detail_no=so.items[0].name,
			reserved_qty=30,
		)

		so.load_from_db()
		sre1.load_from_db()
		self.assertEqual(sre1.status, "Partially Reserved")
		self.assertEqual(so.items[0].stock_reserved_qty, sre1.reserved_qty)

		# Step - 3: Create a `Stock Reservation Entry[2]` for the `Sales Order Item`
		sre2 = make_stock_reservation_entry(
			item_code=item_code,
			warehouse=warehouse,
			voucher_type="Sales Order",
			voucher_no=so.name,
			voucher_detail_no=so.items[0].name,
			reserved_qty=20,
		)

		so.load_from_db()
		sre2.load_from_db()
		self.assertEqual(sre1.status, "Partially Reserved")
		self.assertEqual(so.items[0].stock_reserved_qty, sre1.reserved_qty + sre2.reserved_qty)

		# Step - 4: Cancel `Stock Reservation Entry[1]`
		sre1.cancel()
		so.load_from_db()
		sre1.load_from_db()
		self.assertEqual(sre1.status, "Cancelled")
		self.assertEqual(so.items[0].stock_reserved_qty, sre2.reserved_qty)

		# Step - 5: Cancel `Stock Reservation Entry[2]`
		sre2.cancel()
		so.load_from_db()
		sre2.load_from_db()
		self.assertEqual(sre1.status, "Cancelled")
		self.assertEqual(so.items[0].stock_reserved_qty, 0)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_cant_consume_reserved_stock(self) -> None:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)
		from erpnext.stock.stock_ledger import NegativeStockError

		item_code, warehouse = "SR Item 1", "_Test Warehouse - _TC"

		# Step - 1: Create a `Sales Order`
		so = make_sales_order(
			item_code=item_code,
			warehouse=warehouse,
			qty=50,
			rate=100,
			do_not_submit=True,
		)
		so.reserve_stock = 1  # Stock Reservation Entries will be created on submit
		so.items[0].reserve_stock = 1
		so.save()
		so.submit()

		actual_qty = get_stock_balance(item_code, warehouse)

		# Step - 2: Try to consume (Transfer/Issue/Deliver) the Available Qty via Stock Entry or Delivery Note, should throw `NegativeStockError`.
		se = make_stock_entry(
			item_code=item_code,
			qty=actual_qty,
			from_warehouse=warehouse,
			rate=100,
			purpose="Material Issue",
			do_not_submit=True,
		)
		self.assertRaises(NegativeStockError, se.submit)
		se.cancel()

		# Step - 3: Unreserve the stock and consume the Available Qty via Stock Entry.
		cancel_stock_reservation_entries(so.doctype, so.name)

		se = make_stock_entry(
			item_code=item_code,
			qty=actual_qty,
			from_warehouse=warehouse,
			rate=100,
			purpose="Material Issue",
			do_not_submit=True,
		)
		se.submit()
		se.cancel()


def create_items() -> dict:
	from erpnext.stock.doctype.item.test_item import make_item

	items_details = {
		# Stock Items
		"SR Item 1": {"is_stock_item": 1, "valuation_rate": 100},
		"SR Item 2": {"is_stock_item": 1, "valuation_rate": 200, "stock_uom": "Kg"},
		# Batch Items
		"SR Batch Item 1": {
			"is_stock_item": 1,
			"valuation_rate": 100,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SRBI-1-.#####.",
		},
		"SR Batch Item 2": {
			"is_stock_item": 1,
			"valuation_rate": 200,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SRBI-2-.#####.",
			"stock_uom": "Kg",
		},
		# Serial Item
		"SR Serial Item 1": {
			"is_stock_item": 1,
			"valuation_rate": 100,
			"has_serial_no": 1,
			"serial_no_series": "SRSI-1-.#####",
		},
		# Batch and Serial Item
		"SR Batch and Serial Item 1": {
			"is_stock_item": 1,
			"valuation_rate": 100,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SRBSI-1-.#####.",
			"has_serial_no": 1,
			"serial_no_series": "SRBSI-1-.#####",
		},
	}

	items = {}
	for item_code, properties in items_details.items():
		items[item_code] = make_item(item_code, properties)

	return items


def create_material_receipt(
	items: dict, warehouse: str = "_Test Warehouse - _TC", qty: float = 100
) -> StockEntry:
	se = frappe.new_doc("Stock Entry")
	se.purpose = "Material Receipt"
	se.company = "_Test Company"
	cost_center = frappe.get_value("Company", se.company, "cost_center")
	expense_account = frappe.get_value("Company", se.company, "stock_adjustment_account")

	for item in items.values():
		se.append(
			"items",
			{
				"item_code": item.item_code,
				"t_warehouse": warehouse,
				"qty": qty,
				"basic_rate": item.valuation_rate or 100,
				"conversion_factor": 1.0,
				"transfer_qty": qty,
				"cost_center": cost_center,
				"expense_account": expense_account,
			},
		)

	se.set_stock_entry_type()
	se.insert()
	se.submit()
	se.reload()

	return se


def cancel_all_stock_reservation_entries() -> None:
	sre_list = frappe.db.get_all("Stock Reservation Entry", filters={"docstatus": 1}, pluck="name")

	for sre in sre_list:
		frappe.get_doc("Stock Reservation Entry", sre).cancel()


def make_stock_reservation_entry(**args):
	doc = frappe.new_doc("Stock Reservation Entry")
	args = frappe._dict(args)

	doc.item_code = args.item_code or "SR Item 1"
	doc.warehouse = args.warehouse or "_Test Warehouse - _TC"
	doc.voucher_type = args.voucher_type
	doc.voucher_no = args.voucher_no
	doc.voucher_detail_no = args.voucher_detail_no
	doc.available_qty = args.available_qty or 100
	doc.voucher_qty = args.voucher_qty or 50
	doc.stock_uom = args.stock_uom or "Nos"
	doc.reserved_qty = args.reserved_qty or 50
	doc.delivered_qty = args.delivered_qty or 0
	doc.company = args.company or "_Test Company"

	if args.ignore_validate:
		doc.flags.ignore_validate = True

	if not args.do_not_save:
		doc.save()
		if not args.do_not_submit:
			doc.submit()

	return doc
