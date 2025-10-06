# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from random import randint

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint, today

from erpnext.selling.doctype.sales_order.sales_order import create_pick_list, make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	cancel_stock_reservation_entries,
	get_sre_reserved_qty_details_for_voucher,
	get_stock_reservation_entries_for_voucher,
	has_reserved_stock,
)
from erpnext.stock.utils import get_stock_balance


class TestStockReservationEntry(IntegrationTestCase):
	def setUp(self) -> None:
		self.warehouse = "_Test Warehouse - _TC"
		self.sr_item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100})
		create_material_receipt(items={self.sr_item.name: self.sr_item}, warehouse=self.warehouse, qty=100)

	@IntegrationTestCase.change_settings("Stock Settings", {"allow_negative_stock": 0})
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
		with self.change_settings("Stock Settings", {"enable_stock_reservation": 0}):
			self.assertRaises(frappe.ValidationError, validate_stock_reservation_settings, voucher)

		with self.change_settings("Stock Settings", {"enable_stock_reservation": 1}):
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

		# Case - 1: When `Reserved Qty` is `0`, Available Qty to Reserve = Actual Qty
		available_qty_to_reserve = get_available_qty_to_reserve(self.sr_item.name, self.warehouse)
		expected_available_qty_to_reserve = get_stock_balance(self.sr_item.name, self.warehouse)

		self.assertEqual(available_qty_to_reserve, expected_available_qty_to_reserve)

		# Case - 2: When `Reserved Qty` is `> 0`, Available Qty to Reserve = Actual Qty - Reserved Qty
		sre = make_stock_reservation_entry(
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
			ignore_validate=True,
		)
		available_qty_to_reserve = get_available_qty_to_reserve(self.sr_item.name, self.warehouse)
		expected_available_qty_to_reserve = (
			get_stock_balance(self.sr_item.name, self.warehouse) - sre.reserved_qty
		)

		self.assertEqual(available_qty_to_reserve, expected_available_qty_to_reserve)

	def test_update_status(self) -> None:
		sre = make_stock_reservation_entry(
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
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

	@IntegrationTestCase.change_settings(
		"Stock Settings", {"allow_negative_stock": 0, "enable_stock_reservation": 1}
	)
	def test_update_reserved_qty_in_voucher(self) -> None:
		# Step - 1: Create a `Sales Order`
		so = make_sales_order(
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
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
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
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
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
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

		# Step - 5: Update `Stock Reservation Entry[2]` Reserved Qty
		sre2.reserved_qty += sre1.reserved_qty
		sre2.save()
		so.load_from_db()
		sre1.load_from_db()
		self.assertEqual(sre2.status, "Reserved")
		self.assertEqual(so.items[0].stock_reserved_qty, sre2.reserved_qty)

		# Step - 6: Cancel `Stock Reservation Entry[2]`
		sre2.cancel()
		so.load_from_db()
		sre2.load_from_db()
		self.assertEqual(sre1.status, "Cancelled")
		self.assertEqual(so.items[0].stock_reserved_qty, 0)

	@IntegrationTestCase.change_settings(
		"Stock Settings", {"allow_negative_stock": 0, "enable_stock_reservation": 1}
	)
	def test_cant_consume_reserved_stock(self) -> None:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)
		from erpnext.stock.stock_ledger import NegativeStockError

		# Step - 1: Create a `Sales Order`
		so = make_sales_order(
			item_code=self.sr_item.name,
			warehouse=self.warehouse,
			qty=50,
			rate=100,
			do_not_submit=True,
		)
		so.reserve_stock = 1  # Stock Reservation Entries will be created on submit
		so.items[0].reserve_stock = 1
		so.save()
		so.submit()

		actual_qty = get_stock_balance(self.sr_item.name, self.warehouse)

		# Step - 2: Try to consume (Transfer/Issue/Deliver) the Available Qty via Stock Entry or Delivery Note, should throw `NegativeStockError`.
		se = make_stock_entry(
			item_code=self.sr_item.name,
			qty=actual_qty,
			from_warehouse=self.warehouse,
			rate=100,
			purpose="Material Issue",
			do_not_submit=True,
		)
		self.assertRaises(NegativeStockError, se.submit)
		se.cancel()

		# Step - 3: Unreserve the stock and consume the Available Qty via Stock Entry.
		cancel_stock_reservation_entries(so.doctype, so.name)

		se = make_stock_entry(
			item_code=self.sr_item.name,
			qty=actual_qty,
			from_warehouse=self.warehouse,
			rate=100,
			purpose="Material Issue",
			do_not_submit=True,
		)
		se.submit()
		se.cancel()

	@IntegrationTestCase.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 0,
			"pick_serial_and_batch_based_on": "FIFO",
			"auto_create_serial_and_batch_bundle_for_outward": 1,
		},
	)
	def test_stock_reservation_against_sales_order(self) -> None:
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		items_details = create_items()
		se = create_material_receipt(items_details, self.warehouse, qty=10)

		item_list = []
		for item_code, properties in items_details.items():
			item_list.append(
				{
					"item_code": item_code,
					"warehouse": self.warehouse,
					"qty": randint(11, 100),
					"uom": properties.stock_uom,
					"rate": randint(10, 400),
				}
			)

		so = make_sales_order(
			item_list=item_list,
			warehouse=self.warehouse,
		)

		# Test - 1: Stock should not be reserved if the Available Qty to Reserve is less than the Ordered Qty and Partial Reservation is disabled in Stock Settings.
		with self.change_settings("Stock Settings", {"allow_partial_reservation": 0}):
			so.create_stock_reservation_entries()
			self.assertFalse(has_reserved_stock("Sales Order", so.name))

		# Test - 2: Stock should be Partially Reserved if the Partial Reservation is enabled in Stock Settings.
		with self.change_settings("Stock Settings", {"allow_partial_reservation": 1}):
			so.create_stock_reservation_entries()
			so.load_from_db()
			self.assertTrue(has_reserved_stock("Sales Order", so.name))

			for item in so.items:
				sre_details = get_stock_reservation_entries_for_voucher(
					"Sales Order", so.name, item.name, fields=["reserved_qty", "status"]
				)[0]
				self.assertEqual(item.stock_reserved_qty, sre_details.reserved_qty)
				self.assertEqual(sre_details.status, "Partially Reserved")

			cancel_stock_reservation_entries("Sales Order", so.name)
			se.cancel()

			# Test - 3: Stock should be fully Reserved if the Available Qty to Reserve is greater than the Un-reserved Qty.
			create_material_receipt(items_details, self.warehouse, qty=110)
			so.create_stock_reservation_entries()
			so.load_from_db()

			reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Sales Order", so.name)
			for item in so.items:
				reserved_qty = reserved_qty_details[item.name]
				self.assertEqual(item.stock_reserved_qty, reserved_qty)
				self.assertEqual(item.stock_qty, item.stock_reserved_qty)

			# Test - 4: Stock should get unreserved on cancellation of Stock Reservation Entries.
			cancel_stock_reservation_entries("Sales Order", so.name)
			so.load_from_db()
			self.assertFalse(has_reserved_stock("Sales Order", so.name))

			for item in so.items:
				self.assertEqual(item.stock_reserved_qty, 0)

			# Test - 5: Re-reserve the stock.
			so.create_stock_reservation_entries()
			self.assertTrue(has_reserved_stock("Sales Order", so.name))

			# Test - 6: Stock should get unreserved on cancellation of Sales Order.
			so.cancel()
			so.load_from_db()
			self.assertFalse(has_reserved_stock("Sales Order", so.name))

			for item in so.items:
				self.assertEqual(item.stock_reserved_qty, 0)

			# Create Sales Order and Reserve Stock.
			so = make_sales_order(
				item_list=item_list,
				warehouse=self.warehouse,
				do_not_submit=True,
			)

			for row in so.items:
				row.qty = 80

			so.save()
			so.submit()
			so.create_stock_reservation_entries()

			# Test - 7: Partial Delivery against Sales Order.
			dn1 = make_delivery_note(so.name)

			item_wise_serial_nos = {}

			for item in dn1.items:
				item.qty = 10

			dn1.save()
			for row in dn1.items:
				if row.serial_no:
					item_wise_serial_nos.setdefault(row.item_code, []).extend(get_serial_nos(row.serial_no))

			dn1.submit()

			for item in so.items:
				sre_details = get_stock_reservation_entries_for_voucher(
					"Sales Order", so.name, item.name, fields=["delivered_qty", "status"]
				)[0]
				self.assertGreater(sre_details.delivered_qty, 0)
				self.assertEqual(sre_details.status, "Partially Delivered")

			# Test - 8: Over Delivery against Sales Order, SRE Delivered Qty should not be greater than the SRE Reserved Qty.
			with self.change_settings("Stock Settings", {"over_delivery_receipt_allowance": 100}):
				dn2 = make_delivery_note(so.name)

				for item in dn2.items:
					item.qty = 70

				dn2.save()
				dn2.submit()

			for item in so.items:
				sre_details = get_stock_reservation_entries_for_voucher(
					"Sales Order",
					so.name,
					item.name,
					fields=["reserved_qty", "delivered_qty"],
					ignore_status=True,
				)

				for sre_detail in sre_details:
					self.assertEqual(sre_detail.reserved_qty, sre_detail.delivered_qty)

	@IntegrationTestCase.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_auto_reserve_serial_and_batch(self) -> None:
		items_details = create_items()
		create_material_receipt(items_details, self.warehouse, qty=100)

		item_list = []
		for item_code, properties in items_details.items():
			item_list.append(
				{
					"item_code": item_code,
					"warehouse": self.warehouse,
					"qty": randint(11, 100),
					"uom": properties.stock_uom,
					"rate": randint(10, 400),
				}
			)

		so = make_sales_order(
			item_list=item_list,
			warehouse=self.warehouse,
		)
		so.create_stock_reservation_entries()
		so.load_from_db()

		for item in so.items:
			sre_details = get_stock_reservation_entries_for_voucher(
				"Sales Order", so.name, item.name, fields=["status", "reserved_qty"]
			)[0]

			# Test - 1: SRE Reserved Qty should be updated in Sales Order Item.
			self.assertEqual(item.stock_reserved_qty, sre_details.reserved_qty)

			# Test - 2: SRE status should be `Reserved`.
			self.assertEqual(sre_details.status, "Reserved")

		dn = make_delivery_note(so.name, kwargs={"for_reserved_stock": 1})
		dn.save()
		dn.submit()

		for item in so.items:
			sre_details = get_stock_reservation_entries_for_voucher(
				"Sales Order", so.name, item.name, fields=["status", "delivered_qty", "reserved_qty"]
			)[0]

			# Test - 3: After Delivery Note, SRE status should be `Delivered`.
			self.assertEqual(sre_details.status, "Delivered")

			# Test - 4: After Delivery Note, SRE Delivered Qty should be equal to SRE Reserved Qty.
			self.assertEqual(sre_details.delivered_qty, sre_details.reserved_qty)

		sre = frappe.qb.DocType("Stock Reservation Entry")
		sb_entry = frappe.qb.DocType("Serial and Batch Entry")
		for item in dn.items:
			if item.serial_and_batch_bundle:
				reserved_sb_entries = (
					frappe.qb.from_(sre)
					.inner_join(sb_entry)
					.on(sre.name == sb_entry.parent)
					.select(sb_entry.serial_no, sb_entry.batch_no, sb_entry.qty, sb_entry.delivered_qty)
					.where(
						(sre.voucher_type == "Sales Order")
						& (sre.voucher_no == item.against_sales_order)
						& (sre.voucher_detail_no == item.so_detail)
					)
				).run(as_dict=True)

				reserved_sb_details: set[tuple] = set()
				for sb_details in reserved_sb_entries:
					# Test - 5: After Delivery Note, SB Entry Delivered Qty should be equal to SB Entry Reserved Qty.
					self.assertEqual(sb_details.qty, sb_details.delivered_qty)

					reserved_sb_details.add((sb_details.serial_no, sb_details.batch_no, -1 * sb_details.qty))

				delivered_sb_entries = frappe.db.get_all(
					"Serial and Batch Entry",
					filters={"parent": item.serial_and_batch_bundle},
					fields=["serial_no", "batch_no", "qty"],
					as_list=True,
				)
				delivered_sb_details: set[tuple] = set(delivered_sb_entries)

				# Test - 6: Reserved Serial/Batch Nos should be equal to Delivered Serial/Batch Nos.
				self.assertSetEqual(reserved_sb_details, delivered_sb_details)

		dn.cancel()
		so.load_from_db()

		for item in so.items:
			sre_details = get_stock_reservation_entries_for_voucher(
				"Sales Order",
				so.name,
				item.name,
				fields=["name", "status", "delivered_qty", "reservation_based_on"],
			)[0]

			# Test - 7: After Delivery Note cancellation, SRE status should be `Reserved`.
			self.assertEqual(sre_details.status, "Reserved")

			# Test - 8: After Delivery Note cancellation, SRE Delivered Qty should be `0`.
			self.assertEqual(sre_details.delivered_qty, 0)

			if sre_details.reservation_based_on == "Serial and Batch":
				sb_entries = frappe.db.get_all(
					"Serial and Batch Entry",
					filters={"parenttype": "Stock Reservation Entry", "parent": sre_details.name},
					fields=["delivered_qty"],
				)

				for sb_entry in sb_entries:
					# Test - 9: After Delivery Note cancellation, SB Entry Delivered Qty should be `0`.
					self.assertEqual(sb_entry.delivered_qty, 0)

	@IntegrationTestCase.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_stock_reservation_from_pick_list(self) -> None:
		items_details = create_items()
		create_material_receipt(items_details, self.warehouse, qty=100)

		item_list = []
		for item_code, properties in items_details.items():
			item_list.append(
				{
					"item_code": item_code,
					"warehouse": self.warehouse,
					"qty": randint(11, 100),
					"uom": properties.stock_uom,
					"rate": randint(10, 400),
				}
			)

		so = make_sales_order(
			item_list=item_list,
			warehouse=self.warehouse,
		)
		pl = create_pick_list(so.name)
		pl.save()
		pl.submit()
		pl.create_stock_reservation_entries()
		pl.load_from_db()
		so.load_from_db()

		for item in so.items:
			sre_details = get_stock_reservation_entries_for_voucher(
				"Sales Order", so.name, item.name, fields=["reserved_qty"]
			)[0]

			# Test - 1: SRE Reserved Qty should be updated in Sales Order Item.
			self.assertEqual(item.stock_reserved_qty, sre_details.reserved_qty)

		sre = frappe.qb.DocType("Stock Reservation Entry")
		sb_entry = frappe.qb.DocType("Serial and Batch Entry")
		for location in pl.locations:
			# Test - 2: Reserved Qty should be updated in Pick List Item.
			self.assertEqual(location.stock_reserved_qty, location.qty)

			if location.serial_and_batch_bundle:
				picked_sb_entries = frappe.db.get_all(
					"Serial and Batch Entry",
					filters={"parent": location.serial_and_batch_bundle},
					fields=["serial_no", "batch_no", "qty"],
					as_list=True,
				)
				picked_sb_details: set[tuple] = set(picked_sb_entries)

				reserved_sb_entries = (
					frappe.qb.from_(sre)
					.inner_join(sb_entry)
					.on(sre.name == sb_entry.parent)
					.select(sb_entry.serial_no, sb_entry.batch_no, sb_entry.qty)
					.where(
						(sre.voucher_type == "Sales Order")
						& (sre.voucher_no == location.sales_order)
						& (sre.voucher_detail_no == location.sales_order_item)
						& (sre.from_voucher_type == "Pick List")
						& (sre.from_voucher_no == pl.name)
						& (sre.from_voucher_detail_no == location.name)
					)
				).run(as_dict=True)
				reserved_sb_details: set[tuple] = {
					(sb_details.serial_no, sb_details.batch_no, -1 * sb_details.qty)
					for sb_details in reserved_sb_entries
				}

				# Test - 3: Reserved Serial/Batch Nos should be equal to Picked Serial/Batch Nos.
				self.assertSetEqual(picked_sb_details, reserved_sb_details)

	@IntegrationTestCase.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
			"auto_reserve_stock_for_sales_order_on_purchase": 1,
		},
	)
	def test_stock_reservation_from_purchase_receipt(self) -> None:
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.selling.doctype.sales_order.sales_order import make_material_request
		from erpnext.stock.doctype.material_request.material_request import make_purchase_order

		items_details = create_items()
		create_material_receipt(items_details, self.warehouse, qty=10)

		item_list = []
		for item_code, properties in items_details.items():
			item_list.append(
				{
					"item_code": item_code,
					"warehouse": self.warehouse,
					"qty": randint(11, 100),
					"uom": properties.stock_uom,
					"rate": randint(10, 400),
				}
			)

		so = make_sales_order(
			item_list=item_list,
			warehouse=self.warehouse,
		)

		mr = make_material_request(so.name)
		mr.schedule_date = today()
		mr.save().submit()

		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.save().submit()

		pr = make_purchase_receipt(po.name)
		pr.save().submit()

		for item in pr.items:
			sre, status, reserved_qty = frappe.db.get_value(
				"Stock Reservation Entry",
				{
					"from_voucher_type": "Purchase Receipt",
					"from_voucher_no": pr.name,
					"from_voucher_detail_no": item.name,
				},
				["name", "status", "reserved_qty"],
			)

			# Test - 1: SRE status should be `Reserved`.
			self.assertEqual(status, "Reserved")

			# Test - 2: SRE Reserved Qty should be equal to PR Item Qty.
			self.assertEqual(reserved_qty, item.qty)

			if item.serial_and_batch_bundle:
				sb_details = frappe.db.get_all(
					"Serial and Batch Entry",
					filters={"parent": item.serial_and_batch_bundle},
					fields=["serial_no", "batch_no", "qty"],
					as_list=True,
				)
				reserved_sb_details = frappe.db.get_all(
					"Serial and Batch Entry",
					filters={"parent": sre},
					fields=["serial_no", "batch_no", "qty"],
					as_list=True,
				)

				# Test - 3: Reserved Serial/Batch Nos should be equal to PR Item Serial/Batch Nos.
				self.assertEqual(set(sb_details), set(reserved_sb_details))

	@IntegrationTestCase.change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_consider_reserved_stock_while_cancelling_an_inward_transaction(self) -> None:
		items_details = create_items()
		se = create_material_receipt(items_details, self.warehouse, qty=100)

		item_list = []
		for item_code, properties in items_details.items():
			item_list.append(
				{
					"item_code": item_code,
					"warehouse": self.warehouse,
					"qty": randint(11, 100),
					"uom": properties.stock_uom,
					"rate": randint(10, 400),
				}
			)

		so = make_sales_order(
			item_list=item_list,
			warehouse=self.warehouse,
		)
		so.create_stock_reservation_entries()

		# Test - 1: ValidationError should be thrown as the inwarded stock is reserved.
		self.assertRaises(frappe.ValidationError, se.cancel)

	def tearDown(self) -> None:
		cancel_all_stock_reservation_entries()
		return super().tearDown()


def create_items() -> dict:
	items_properties = [
		# SR STOCK ITEM
		{"is_stock_item": 1, "valuation_rate": 100},
		# SR SERIAL ITEM
		{
			"is_stock_item": 1,
			"valuation_rate": 200,
			"has_serial_no": 1,
			"serial_no_series": "SRSI-.#####",
		},
		# SR BATCH ITEM
		{
			"is_stock_item": 1,
			"valuation_rate": 300,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SRBI-.#####.",
		},
		# SR SERIAL AND BATCH ITEM
		{
			"is_stock_item": 1,
			"valuation_rate": 400,
			"has_serial_no": 1,
			"serial_no_series": "SRSBI-.#####",
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "SRSBI-.#####.",
		},
	]

	items = {}
	for properties in items_properties:
		item = make_item(properties=properties)
		items[item.name] = item

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

	doc.item_code = args.item_code
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
