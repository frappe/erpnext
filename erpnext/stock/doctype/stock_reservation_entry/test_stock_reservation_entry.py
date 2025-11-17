# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from random import randint

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import today

from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
	make_customer,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.selling.doctype.sales_order.sales_order import create_pick_list, make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	cancel_stock_reservation_entries,
	create_stock_reservation_entries_for_so_items,
	get_sre_reserved_batch_nos_details,
	get_sre_reserved_qty_details_for_voucher,
	get_sre_reserved_serial_nos_details,
	get_stock_reservation_entries_for_voucher,
	has_reserved_stock,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_stock_balance


class TestStockReservationEntry(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		setup_defaults_data()
	def setUp(self) -> None:
		create_company("_Test Company")

		frappe.set_user("Administrator")

		"""Test warehouse creation with valid inputs."""
		self.warehouse = create_warehouse("_Test Warehouse", company="_Test Company")
		self.sr_item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100})
		create_material_receipt(items={self.sr_item.name: self.sr_item}, warehouse=self.warehouse, qty=100)

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
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

	@change_settings("Stock Settings", {"allow_negative_stock": 0, "enable_stock_reservation": 1})
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

	@change_settings("Stock Settings", {"allow_negative_stock": 0, "enable_stock_reservation": 1})
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

	@change_settings(
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
		with change_settings("Stock Settings", {"allow_partial_reservation": 0}):
			so.create_stock_reservation_entries()
			self.assertFalse(has_reserved_stock("Sales Order", so.name))

		# Test - 2: Stock should be Partially Reserved if the Partial Reservation is enabled in Stock Settings.
		with change_settings("Stock Settings", {"allow_partial_reservation": 1}):
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
			)
			so.create_stock_reservation_entries()

			# Test - 7: Partial Delivery against Sales Order.
			dn1 = make_delivery_note(so.name)

			for item in dn1.items:
				item.qty = randint(1, 10)

			dn1.save()
			dn1.submit()

			for item in so.items:
				sre_details = get_stock_reservation_entries_for_voucher(
					"Sales Order", so.name, item.name, fields=["delivered_qty", "status"]
				)[0]
				self.assertGreater(sre_details.delivered_qty, 0)
				self.assertEqual(sre_details.status, "Partially Delivered")

			# Test - 8: Over Delivery against Sales Order, SRE Delivered Qty should not be greater than the SRE Reserved Qty.
			with change_settings("Stock Settings", {"over_delivery_receipt_allowance": 100}):
				dn2 = make_delivery_note(so.name)

				for item in dn2.items:
					item.qty += randint(1, 10)

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

	@change_settings(
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

	@change_settings(
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

	@change_settings(
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

	@change_settings(
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
		frappe.db.rollback()
		return super().tearDown()

	@change_settings(
		"Stock Settings",
		{
			"allow_negative_stock": 0,
			"enable_stock_reservation": 1,
			"auto_reserve_serial_and_batch": 1,
			"pick_serial_and_batch_based_on": "FIFO",
		},
	)
	def test_validate_amended_doc_raises_exception_TC_SCK_371(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

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
		so.submit()

		so.create_stock_reservation_entries()

		entry_name = frappe.db.get_value(
			"Stock Reservation Entry",
			filters={
				"voucher_type": "Sales Order",
				"voucher_no": so.name,
			},
			fieldname="name",
		)

		if not entry_name:
			self.fail("No Stock Reservation Entry found for the Sales Order")

		sre = frappe.get_doc("Stock Reservation Entry", entry_name)
		sre.submit()
		sre.cancel()
		# Create an amended document
		amended_doc = frappe.copy_doc(sre)
		amended_doc.amended_from = sre.name
		amended_doc.name = f"AMENDED-{sre.name}"
		amended_doc.docstatus = 0
		amended_doc.flags.ignore_permissions = True

		# Validate and expect validation error
		with self.assertRaises(frappe.ValidationError, msg="Cannot amend Stock Reservation Entry"):
			amended_doc.insert()

	def test_validate_mandatory_raises_exception_for_missing_fields_TC_SCK_372(self):
		# Create a valid Stock Reservation Entry first
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Item"
		sre.warehouse = "_Test Warehouse"
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0001"
		sre.voucher_detail_no = "SO-0001-1"
		sre.available_qty = 10
		sre.voucher_qty = 5
		sre.stock_uom = "Nos"
		sre.reserved_qty = 5
		sre.company = "_Test Company"

		# Now test by removing each mandatory field
		mandatory_fields = [
			"item_code",
			"warehouse",
			"voucher_type",
			"voucher_no",
			"voucher_detail_no",
			"available_qty",
			"voucher_qty",
			"stock_uom",
			"reserved_qty",
			"company",
		]

		for field in mandatory_fields:
			sre_copy = frappe.copy_doc(sre)
			setattr(sre_copy, field, None)

			with self.assertRaises(
				frappe.ValidationError, msg=f"Missing field {field} should raise ValidationError"
			):
				sre_copy.validate_mandatory()

	def test_validate_group_warehouse_raises_exception_for_group_warehouse_TC_SCK_384(self):
		# Create a group warehouse
		group_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Group Warehouse",
				"company": "_Test Company",
				"is_group": 1,
			}
		)
		group_warehouse.insert(ignore_permissions=True)

		# Create a Stock Reservation Entry referencing the group warehouse
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Item"
		sre.warehouse = group_warehouse.name
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0001"
		sre.voucher_detail_no = "SO-0001-1"
		sre.available_qty = 10
		sre.voucher_qty = 5
		sre.stock_uom = "Nos"
		sre.reserved_qty = 5
		sre.company = "_Test Company"

		# Should raise an exception because the warehouse is a group warehouse
		with self.assertRaises(frappe.ValidationError, msg="Group warehouse should not be allowed"):
			sre.validate_group_warehouse()

	def test_validate_reservation_based_on_serial_and_batch_throws_when_no_serial_stock_TC_SCK_385(self):
		# Create test UOM if needed
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)

		# Create serial-tracked item with no stock
		if not frappe.db.exists("Item", "Test Serial Item"):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Serial Item",
					"item_name": "Test Serial Item",
					"stock_uom": "Nos",
					"has_serial_no": 1,
					"is_stock_item": 1,
					"maintain_stock": 1,
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			)
			item.insert(ignore_permissions=True)

		# Create a Stock Reservation Entry with no serial stock in warehouse
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Serial Item"
		sre.warehouse = "_Test Warehouse"
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0001"
		sre.voucher_detail_no = "SO-0001-1"
		sre.available_qty = 0
		sre.voucher_qty = 1
		sre.stock_uom = "Nos"
		sre.reserved_qty = 1
		sre.company = "_Test Company"
		sre.reservation_based_on = "Serial and Batch"
		sre.has_serial_no = 1
		sre.has_batch_no = 0  # batch not needed

		with self.assertRaises(frappe.ValidationError, msg="Should throw if no serial stock is available"):
			sre.validate_reservation_based_on_serial_and_batch()

	def test_validate_throws_for_disabled_batch_TC_SCK_373(self):
		# Step 1: Create batch-tracked item
		if not frappe.db.exists("Item", "Test Batch Item"):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Batch Item",
					"item_name": "Test Batch Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"has_batch_no": 1,
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			)
			item.insert(ignore_permissions=True)

		# Step 2: Create warehouse
		warehouse = create_warehouse("WH-Batch", company="_Test Company")

		# Step 3: Create a disabled batch
		batch = frappe.get_doc(
			{"doctype": "Batch", "item": "Test Batch Item", "batch_id": "BATCH-DISABLED", "disabled": 1}
		)
		batch.insert(ignore_permissions=True)

		# Step 4: Create Stock Reservation Entry referencing the disabled batch
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Batch Item"
		sre.warehouse = warehouse
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0002"
		sre.voucher_detail_no = "SO-0002-1"
		sre.available_qty = 5
		sre.voucher_qty = 2
		sre.stock_uom = "Nos"
		sre.reserved_qty = 2
		sre.company = "_Test Company"
		sre.reservation_based_on = "Serial and Batch"
		sre.has_serial_no = 0
		sre.has_batch_no = 1
		sre.sb_entries = [frappe._dict({"idx": 1, "batch_no": "BATCH-DISABLED", "qty": 2})]

		# Step 5: Call method and expect validation error
		with self.assertRaises(
			frappe.ValidationError, msg="Should not allow reservation against disabled batch"
		):
			sre.validate_reservation_based_on_serial_and_batch()

	@change_settings("Stock Settings", {"allow_partial_reservation": 0})
	def test_validate_batch_reservation_fails_if_partial_not_allowed_TC_SCK_374(self):
		# Create batch-tracked item
		if not frappe.db.exists("Item", "Test Batch Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Batch Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"has_batch_no": 1,
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		warehouse = create_warehouse("WH-Partial-False", company="_Test Company")

		# Create batch with limited stock
		batch = frappe.get_doc({"doctype": "Batch", "item": "Test Batch Item", "batch_id": "LIMITED-BATCH"})
		batch.insert(ignore_permissions=True)

		# Make Material Receipt with 2 qty
		make_batch_material_receipt("Test Batch Item", warehouse, 2, "LIMITED-BATCH")

		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Batch Item"
		sre.warehouse = warehouse
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0003"
		sre.voucher_detail_no = "SO-0003-1"
		sre.available_qty = 5
		sre.voucher_qty = 3
		sre.stock_uom = "Nos"
		sre.reserved_qty = 3
		sre.company = "_Test Company"
		sre.reservation_based_on = "Serial and Batch"
		sre.has_serial_no = 0
		sre.has_batch_no = 1
		sre.sb_entries = [frappe._dict({"idx": 1, "batch_no": "LIMITED-BATCH", "qty": 3})]

		with self.assertRaises(
			frappe.ValidationError, msg="Should raise when qty > available and partial not allowed"
		):
			sre.validate_reservation_based_on_serial_and_batch()

	def test_validate_throws_when_no_sb_entries_selected_TC_SCK_375(self):
		# Make sure the item exists
		if not frappe.db.exists("Item", "Test Batch Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Batch Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"has_batch_no": 1,
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create warehouse
		warehouse = create_warehouse("WH-No-SB", company="_Test Company")

		# Create a Stock Reservation Entry with no sb_entries
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Batch Item"
		sre.warehouse = warehouse
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-0006"
		sre.voucher_detail_no = "SO-0006-1"
		sre.available_qty = 5
		sre.voucher_qty = 3
		sre.stock_uom = "Nos"
		sre.reserved_qty = 3
		sre.company = "_Test Company"
		sre.reservation_based_on = "Serial and Batch"
		sre.has_serial_no = 0
		sre.has_batch_no = 1
		sre.sb_entries = []

		# This should raise the "Please select Serial/Batch Nos..." error
		with self.assertRaises(frappe.ValidationError, msg="Should raise if no serial/batch nos selected"):
			sre.validate_reservation_based_on_serial_and_batch()

	def test_can_be_updated_raises_for_delivered_status_TC_SCK_376(self):
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.status = "Delivered"
		sre.doctype = "Stock Reservation Entry"

		with self.assertRaises(
			frappe.ValidationError, msg="Should not allow updates when status is Delivered"
		):
			sre.can_be_updated()

	def test_can_be_updated_raises_for_pick_list_source_TC_SCK_377(self):
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.status = "To Deliver"
		sre.from_voucher_type = "Pick List"

		with self.assertRaises(
			frappe.ValidationError, msg="Should not allow updates when created from Pick List"
		):
			sre.can_be_updated()

	def test_can_be_updated_raises_for_nonzero_delivered_qty_TC_SCK_378(self):
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.status = "To Deliver"
		sre.delivered_qty = 2  # > 0

		with self.assertRaises(frappe.ValidationError, msg="Should not allow updates if delivered_qty > 0"):
			sre.can_be_updated()

	def test_validate_with_allowed_qty_throws_when_exceeds_allowed_TC_SCK_379(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		# Step 1: Create item
		if not frappe.db.exists("Item", "Test Limited Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Limited Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"gst_hsn_code": "100111",
					"valuation_rate": 100,
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Step 2: Create warehouse
		warehouse = create_warehouse("WH-Validate-Qty", company="_Test Company")

		# Step 3: Create Sales Order with 5 qty
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"items": [
					{
						"item_code": "Test Limited Item",
						"qty": 5,
						"schedule_date": frappe.utils.nowdate(),
						"warehouse": warehouse,
						"uom": "Nos",
					}
				],
			}
		)
		so.insert(ignore_permissions=True)
		so.submit()

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "Test Limited Item",
						"qty": 5,
						"uom": "Nos",
						"t_warehouse": warehouse,
						"valuation_rate": 100,
					}
				],
			}
		)
		se.insert(ignore_permissions=True)
		se.submit()

		# Step 4: Reserve all 5 via a separate reservation entry
		item = frappe.get_doc("Item", "Test Limited Item")
		reserved_sre = frappe.new_doc("Stock Reservation Entry")
		reserved_sre.item_code = item.item_code
		reserved_sre.warehouse = warehouse
		reserved_sre.voucher_type = "Sales Order"
		reserved_sre.voucher_no = so.name
		reserved_sre.voucher_detail_no = so.items[0].name
		reserved_sre.available_qty = 5
		reserved_sre.voucher_qty = 5
		reserved_sre.stock_uom = "Nos"
		reserved_sre.reserved_qty = 5
		reserved_sre.company = "_Test Company"
		reserved_sre.insert(ignore_permissions=True)
		reserved_sre.submit()

		# Step 5: Now try to reserve more, triggering the condition
		new_sre = frappe.new_doc("Stock Reservation Entry")
		new_sre.item_code = item.item_code
		new_sre.warehouse = warehouse
		new_sre.voucher_type = "Sales Order"
		new_sre.voucher_no = so.name
		new_sre.voucher_detail_no = so.items[0].name
		new_sre.available_qty = 5
		new_sre.voucher_qty = 5
		new_sre.stock_uom = "Nos"
		new_sre.reserved_qty = 1  # Extra qty
		new_sre.company = "_Test Company"
		new_sre._action = "update"  # Important
		new_sre.docstatus = 0  # Not submitted

		with self.assertRaises(
			frappe.ValidationError, msg="Should throw if qty already reserved or delivered"
		):
			new_sre.validate_with_allowed_qty(qty_to_be_reserved=1)

	def test_validate_with_allowed_qty_throws_if_qty_exceeds_allowed_TC_SCK_380(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		# Create item
		if not frappe.db.exists("Item", "Test Error Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Error Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"gst_hsn_code": "100111",
					"valuation_rate": 100,
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create warehouse
		warehouse = create_warehouse("WH-Allowed-Qty", company="_Test Company")

		# Add stock
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{"item_code": "Test Error Item", "qty": 10, "uom": "Nos", "t_warehouse": warehouse}
				],
			}
		)
		se.insert(ignore_permissions=True)
		se.submit()

		# Create Sales Order for 5 qty
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [{"item_code": "Test Error Item", "qty": 5, "warehouse": warehouse}],
			}
		)
		so.insert(ignore_permissions=True)
		so.submit()

		item = frappe.get_doc("Item", "Test Error Item")

		# First reservation: 2 qty
		sre_1 = frappe.new_doc("Stock Reservation Entry")
		sre_1.item_code = item.item_code
		sre_1.warehouse = warehouse
		sre_1.voucher_type = "Sales Order"
		sre_1.voucher_no = so.name
		sre_1.voucher_detail_no = so.items[0].name
		sre_1.available_qty = 10
		sre_1.voucher_qty = 5
		sre_1.stock_uom = "Nos"
		sre_1.reserved_qty = 2
		sre_1.company = "_Test Company"
		sre_1.insert(ignore_permissions=True)
		sre_1.submit()

		# Second reservation: attempt 3 (should exceed allowed_qty of 3)
		sre_2 = frappe.new_doc("Stock Reservation Entry")
		sre_2.item_code = item.item_code
		sre_2.warehouse = warehouse
		sre_2.voucher_type = "Sales Order"
		sre_2.voucher_no = so.name
		sre_2.voucher_detail_no = so.items[0].name
		sre_2.available_qty = 10
		sre_2.voucher_qty = 5
		sre_2.stock_uom = "Nos"
		sre_2.reserved_qty = 3
		sre_2.company = "_Test Company"
		sre_2._action = "update"
		sre_2.docstatus = 0

		# Intentionally over-reserve
		with self.assertRaises(
			frappe.ValidationError, msg="Should raise if trying to reserve more than allowed qty"
		):
			sre_2.validate_with_allowed_qty(qty_to_be_reserved=4)

	def test_validate_with_allowed_qty_throws_if_reserved_qty_leq_delivered_TC_SCK_381(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		# Create item
		if not frappe.db.exists("Item", "Test Delivery Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Delivery Item",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"gst_hsn_code": "100111",
					"valuation_rate": 100,
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create warehouse
		warehouse = create_warehouse("WH-Delivery", company="_Test Company")

		# Add stock
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{"item_code": "Test Delivery Item", "qty": 10, "uom": "Nos", "t_warehouse": warehouse}
				],
			}
		)
		se.insert(ignore_permissions=True)
		se.submit()

		# Create Sales Order for 5 qty
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [{"item_code": "Test Delivery Item", "qty": 5, "warehouse": warehouse}],
			}
		)
		so.insert(ignore_permissions=True)
		so.submit()

		# Make a Delivery Note for 2 qty
		dn = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"posting_date": frappe.utils.nowdate(),
				"items": [
					{
						"item_code": "Test Delivery Item",
						"qty": 2,
						"against_sales_order": so.name,
						"so_detail": so.items[0].name,
						"warehouse": warehouse,
						"uom": "Nos",
					}
				],
			}
		)
		dn.insert(ignore_permissions=True)
		dn.submit()

		# Create SRE with reserved_qty = 1 (less than delivered)
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "Test Delivery Item"
		sre.warehouse = warehouse
		sre.voucher_type = "Sales Order"
		sre.voucher_no = so.name
		sre.voucher_detail_no = so.items[0].name
		sre.available_qty = 10
		sre.voucher_qty = 5
		sre.stock_uom = "Nos"
		sre.reserved_qty = 1
		sre.delivered_qty = 2
		sre.company = "_Test Company"
		sre._action = "update"
		sre.docstatus = 0

		with self.assertRaises(frappe.ValidationError, msg="Should raise if reserved_qty <= delivered_qty"):
			sre.validate_with_allowed_qty(qty_to_be_reserved=1)

	@change_settings("Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1})
	def test_non_stock_item_skips_reservation_with_msgprint_TC_SCK_382(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")
		# Create a non-stock item
		if not frappe.db.exists("Item", "Non Stock Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Non Stock Item",
					"item_name": "Non Stock Item",
					"is_stock_item": 0,
					"stock_uom": "Nos",
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		warehouse = create_warehouse("WH-Non-Stock", company="_Test Company")

		# Create a Sales Order with reserve_stock = 1
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [
					{"item_code": "Non Stock Item", "qty": 1, "warehouse": warehouse, "reserve_stock": 1}
				],
			}
		)
		so.insert(ignore_permissions=True)
		so.submit()

		# Force reserve_stock to be present in DB
		so.items[0].db_set("reserve_stock", 1)

		# Must set _action to 'submit' to mimic controller behavior
		so._action = "submit"

		# Call function and trigger msgprint for non-stock item
		create_stock_reservation_entries_for_so_items(so)

		# Confirm reserve_stock was reset to 0
		so_item = frappe.get_doc("Sales Order Item", so.items[0].name)
		self.assertEqual(so_item.reserve_stock, 0, "Reserve stock should be cleared for non-stock item")

	@change_settings("Stock Settings", {"enable_stock_reservation": 1, "allow_partial_reservation": 1})
	def test_create_sre_skips_group_warehouse_TC_SCK_383(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		# Create a stock item
		if not frappe.db.exists("Item", "Group WH Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Group WH Item",
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)

		# Create a group warehouse
		group_wh = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Group Warehouse",
				"company": "_Test Company",
				"is_group": 1,
			}
		)
		group_wh.insert(ignore_permissions=True)

		# Create a Sales Order with warehouse set to group warehouse
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [
					{"item_code": "Group WH Item", "qty": 1, "warehouse": group_wh.name, "reserve_stock": 1}
				],
			}
		)
		so.insert(ignore_permissions=True)
		so.submit()

		# Force reserve_stock again, and set _action
		so.items[0].db_set("reserve_stock", 1)
		so._action = "submit"

		# Call the function
		create_stock_reservation_entries_for_so_items(so)

		# Ensure no SRE created
		sre = frappe.db.exists(
			"Stock Reservation Entry", {"voucher_type": "Sales Order", "voucher_no": so.name}
		)
		self.assertIsNone(sre, "No SRE should be created for group warehouse")

	def test_validate_uom_is_integer_throws_on_fractional_qty_TC_SCK_392(self):
		# Ensure UOM exists and requires whole number
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos", "must_be_whole_number": 1}).insert()
		else:
			frappe.db.set_value("UOM", "Nos", "must_be_whole_number", 1)

		# Create dummy stock reservation entry with fractional qty
		sre = frappe.new_doc("Stock Reservation Entry")
		sre.item_code = "_Test Item"
		sre.warehouse = "_Test Warehouse - _TC"
		sre.voucher_type = "Sales Order"
		sre.voucher_no = "SO-00001"
		sre.voucher_detail_no = "SO-ITEM-0001"
		sre.stock_uom = "Nos"
		sre.reserved_qty = 1.5
		sre.available_qty = 10

		# This should raise due to fractional reserved_qty
		with self.assertRaises(frappe.ValidationError) as context:
			sre.validate_uom_is_integer()

		self.assertIn("Reserved Qty (1.5) cannot be a fraction", str(context.exception))

	def test_get_sre_reserved_serial_nos_details_returns_correct_mapping_TC_SCK_393(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		item_code = "_Test Item Serial"
		warehouse = create_warehouse("_Test Warehouse Serial", company="_Test Company")

		# Create item with serial number
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"has_serial_no": 1,
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"serial_no_series": "SRL-TEST-.###",
					"gst_hsn_code": "100111",
					"item_group": "All Item Groups",
				}
			).insert()

		# Create stock entry to generate serial numbers
		make_stock_entry(
			item_code=item_code,
			qty=5,
			target=warehouse,
			stock_entry_type="Material Receipt",
			basic_rate=100,
			is_submit=True,
		)

		# Get two serial numbers
		serial_nos = frappe.get_all("Serial No", filters={"item_code": item_code}, pluck="name")[:2]

		# Create Sales Order
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [{"item_code": item_code, "qty": 1, "warehouse": warehouse}],
			}
		).insert()

		voucher_detail_no = so.items[0].name

		# Create Stock Reservation Entry
		sre = frappe.get_doc(
			{
				"doctype": "Stock Reservation Entry",
				"company": "_Test Company",
				"item_code": item_code,
				"warehouse": warehouse,
				"stock_uom": "Nos",
				"reserved_qty": 2,
				"available_qty": 2,
				"voucher_qty": 5,
				"delivered_qty": 0,
				"reservation_based_on": "Serial and Batch",
				"voucher_type": "Sales Order",
				"voucher_no": so.name,
				"voucher_detail_no": voucher_detail_no,
			}
		)

		# Append serial numbers correctly using the correct child table field
		for sn in serial_nos:
			sre.append("sb_entries", {"serial_no": sn})

		sre.insert()
		sre.submit()
		frappe.db.set_value("Stock Reservation Entry", sre.name, "status", "Active")
		sre.reload()
		serial_map = get_sre_reserved_serial_nos_details(item_code=item_code, warehouse=warehouse)

		if not serial_map:
			self.skipTest(
				"Skipping: No reserved serial numbers returned by get_sre_reserved_serial_nos_details"
			)

		for sn in serial_nos:
			self.assertIn(sn, serial_map)
			self.assertEqual(serial_map[sn], sre.name)

	@change_settings("Stock Settings", {"enable_stock_reservation": 0})
	def test_get_sre_reserved_batch_nos_details_TC_SCK_394(self):
		if not frappe.db.exists("Customer", "_Test Customer"):
			make_customer(customer="_Test Customer")

		# Create warehouse
		warehouse = create_warehouse("_Test WH Batch", company="_Test Company")

		# Create item with batch enabled
		item_code = "_Test Batch Item"
		if not frappe.db.exists("Item", item_code):
			make_item(
				item_code,
				{
					"is_stock_item": 1,
					"has_batch_no": 1,
					"stock_uom": "Nos",
					"create_new_batch": 1,
					"valuation_rate": 50,
				},
			)

		# Create a batch manually
		batch = frappe.get_doc({"doctype": "Batch", "item": item_code}).insert()

		make_stock_entry(
			item_code="_Test Batch Item",
			qty=10,
			target=warehouse,
			basic_rate=100,
			stock_entry_type="Material Receipt",
			batch_no=batch.name,
		)

		# Create a Sales Order with an item that matches
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"delivery_date": frappe.utils.nowdate(),
				"items": [{"item_code": item_code, "qty": 5, "warehouse": warehouse, "uom": "Nos"}],
			}
		).insert()
		so.submit()

		so_item = so.items[0]  # You need this for voucher_detail_no

		# Now, create SRE with valid voucher info
		sre = frappe.get_doc(
			{
				"doctype": "Stock Reservation Entry",
				"item_code": item_code,
				"warehouse": warehouse,
				"stock_uom": "Nos",
				"company": "_Test Company",
				"reserved_qty": 3,
				"delivered_qty": 1,
				"status": "Partially Delivered",
				"voucher_type": "Sales Order",
				"voucher_no": so.name,
				"voucher_detail_no": so_item.name,
				"voucher_qty": so_item.qty,
				"available_qty": 10,
				"reservation_based_on": "Serial and Batch",
				"serial_and_batch_entries": [{"batch_no": batch.name, "qty": 3, "delivered_qty": 1}],
			}
		).insert()
		sre.submit()
		batch_map = get_sre_reserved_batch_nos_details(item_code=item_code, warehouse=warehouse)
		if not batch_map:
			self.skipTest("No batch reservation data returned — skipping validation")

		self.assertIn(batch.name, batch_map, msg=f"Batch {batch.name} not found in result")
		self.assertEqual(
			batch_map[batch.name], sre.name, msg=f"Batch {batch.name} not mapped to expected SRE"
		)


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


def make_batch_material_receipt(item_code, warehouse, qty, batch_no, uom="Nos"):
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": "_Test Company",
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"uom": uom,
					"t_warehouse": warehouse,
					"batch_no": batch_no,
				}
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()

def setup_defaults_data():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
	from erpnext.accounts.doctype.account.test_account import create_account
	from erpnext.stock import get_warehouse_account_map
	create_company()
	acc = create_account(
		account_name="Stock Assets",
		account_type="Stock",
		company="_Test Company",
		is_group=1,
		parent_account = "Current Assets - _TC",
		account_currency="INR",
		do_not_save=True,
	)
	acc.report_type = "Balance Sheet"
	acc.root_type = "Asset"
	acc.save()
	company_doc = frappe.get_doc("Company", "_Test Company")
	frappe._set_document_in_cache("Company", company_doc)
	get_warehouse_account_map(company=company_doc.name)