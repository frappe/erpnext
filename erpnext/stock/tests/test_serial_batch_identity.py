from unittest.mock import patch

import frappe
from frappe.utils import get_url_to_form

from erpnext.controllers.sales_and_purchase_return import get_returned_serial_nos
from erpnext.controllers.selling_controller import get_delivered_serial_batch_for_reservation
from erpnext.controllers.subcontracting_controller import add_items_in_ste
from erpnext.manufacturing.doctype.work_order.mapper import get_serial_nos_for_job_card
from erpnext.selling.page.point_of_sale.point_of_sale import (
	filter_result_items,
	get_serials_by_batch,
	search_by_term,
	search_for_serial_or_batch_or_barcode_number,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.pick_list.pick_list import (
	get_items_with_location_and_quantity,
	get_pick_list_holders,
)
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_reserved_serial_nos_for_pos,
	get_serial_batch_numbers,
	get_serial_batch_scan,
)
from erpnext.stock.doctype.serial_no.serial_no import auto_fetch_serial_number, get_pos_reserved_serial_nos
from erpnext.stock.doctype.stock_entry.services.disassemble import (
	DisassembleStockEntry,
	get_available_materials,
)
from erpnext.stock.doctype.stock_entry.services.manufacturing import ManufactureStockEntry
from erpnext.stock.doctype.stock_entry.services.serial_batch import StockEntrySABB
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_items, get_stock_balance_for
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import get_reserved_materials
from erpnext.stock.get_item_details import get_filtered_serial_nos, update_stock
from erpnext.stock.report.stock_ledger.stock_ledger import update_available_serial_nos
from erpnext.stock.serial_batch_bundle import get_serial_batch_list_from_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchIdentity(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Identity Item A", {"has_serial_no": 1, "has_batch_no": 1})
		self.other_item = make_item("_Identity Item B", {"has_serial_no": 1, "has_batch_no": 1})

	def test_resolution_preserves_order_and_repeated_numbers(self):
		for doctype in ("Serial No", "Batch"):
			with self.subTest(doctype=doctype):
				first = self.make_number(doctype, "First-001")
				second = self.make_number(doctype, "Second-002")
				numbers = [" second-002 ", "FIRST-001", "Second-002"]
				self.assertEqual(
					SerialBatchIdentity(doctype).resolve(self.item.name, numbers),
					[second.name, first.name, second.name],
				)
				self.assertEqual(numbers, [" second-002 ", "FIRST-001", "Second-002"])
				self.assertEqual(first.reload().get(SerialBatchIdentity(doctype).number_field), "First-001")

	def test_label_lookup_preserves_order_repetitions_and_spelling(self):
		for doctype in ("Serial No", "Batch"):
			with self.subTest(doctype=doctype):
				first = self.make_number(doctype, "Physical-001")
				second = self.make_number(doctype, "Physical-002")
				self.make_number(doctype, "Physical-001", self.other_item.name)
				names = [second.name, first.name, second.name]
				identity = SerialBatchIdentity(doctype)
				self.assertEqual(
					identity.get_numbers(self.item.name, names),
					["Physical-002", "Physical-001", "Physical-002"],
				)
				self.assertEqual(names, [second.name, first.name, second.name])
				self.assertEqual(identity.get_numbers(self.item.name, []), [])

	def test_label_lookup_refuses_records_of_another_item(self):
		for doctype in ("Serial No", "Batch"):
			with self.subTest(doctype=doctype):
				record = self.make_number(doctype, "Unlinked-001")
				identity = SerialBatchIdentity(doctype)
				with self.assertRaisesRegex(frappe.DoesNotExistError, "Unlinked-001.*_Identity Item B"):
					identity.get_numbers(self.other_item.name, [record.name])
				with self.assertRaises(frappe.DoesNotExistError):
					identity.get_numbers(self.item.name, [record.name, "Missing-ID"])

	def test_resolution_spans_match_chunks(self):
		first = self.make_number("Serial No", "Chunk-001")
		second = self.make_number("Serial No", "Chunk-002")
		numbers = ["Chunk-001", "Chunk-new", "Chunk-002", "CHUNK-NEW", "Chunk-001"]
		with patch("erpnext.stock.serial_batch_identity.MATCH_CHUNK_SIZE", 2):
			names = SerialBatchIdentity("Serial No").resolve(
				self.item.name, numbers, create=True, defaults={"company": "_Test Company"}
			)
		created = names[1]
		self.assertEqual(names, [first.name, created, second.name, created, first.name])
		self.assertEqual(
			frappe.db.count(
				"Serial No", {"item_code": self.item.name, "serial_no": ("in", ["Chunk-new", "CHUNK-NEW"])}
			),
			1,
		)

	def test_resolution_uses_the_selected_item(self):
		for doctype in ("Serial No", "Batch"):
			self.make_number(doctype, "Physical-001")
			with self.assertRaisesRegex(frappe.ValidationError, "Physical-001.*_Identity Item B"):
				SerialBatchIdentity(doctype).resolve(self.other_item.name, ["Physical-001"])

	def test_numbers_are_not_interpreted_as_ids(self):
		for doctype in ("Serial No", "Batch"):
			first = self.make_number(doctype, "Physical-001")
			second = self.make_number(doctype, first.name)
			self.assertEqual(
				SerialBatchIdentity(doctype).resolve(self.item.name, [first.name]), [second.name]
			)

	def test_missing_numbers_are_not_created(self):
		for doctype in ("Serial No", "Batch"):
			count = frappe.db.count(doctype)
			with self.assertRaisesRegex(frappe.DoesNotExistError, "Missing-001.*_Identity Item A"):
				SerialBatchIdentity(doctype).resolve(self.item.name, ["Missing-001"])
			self.assertEqual(frappe.db.count(doctype), count)

	def test_empty_input(self):
		for doctype in ("Serial No", "Batch"):
			self.assertEqual(SerialBatchIdentity(doctype).resolve(self.item.name, []), [])

	def test_invalid_input(self):
		identity = SerialBatchIdentity("Serial No")
		for numbers in ("Serial-001", [None], [1], [" "], None):
			with self.subTest(numbers=numbers), self.assertRaises(frappe.ValidationError):
				identity.resolve(self.item.name, numbers)
		with self.assertRaisesRegex(frappe.ValidationError, "Item is required"):
			identity.resolve(None, ["Serial-001"])

	def test_lookup_requires_permission(self):
		for doctype in ("Serial No", "Batch"):
			self.make_number(doctype, "Physical-001")
			with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
				SerialBatchIdentity(doctype).resolve(self.item.name, ["Physical-001"])

	def test_scan_lookup_returns_the_selected_items_record(self):
		for item in (self.item, self.other_item):
			batch = self.make_number("Batch", "Scan-Batch", item.name)
			serial = self.make_number("Serial No", "Scan-Serial", item.name)
			serial.batch_no = batch.name
			serial.save()
			self.assertEqual(
				get_serial_batch_scan(item.name, " scan-serial ", "Serial No"),
				{"name": serial.name, "serial_no": "Scan-Serial", "batch_no": batch.name},
			)
			self.assertEqual(
				get_serial_batch_scan(item.name, " SCAN-BATCH ", "Batch"),
				{"name": batch.name, "batch_id": "Scan-Batch"},
			)

	def test_scan_lookup_does_not_create_or_interpret_ids(self):
		for doctype in ("Serial No", "Batch"):
			record = self.make_number(doctype, "Scan-001")
			count = frappe.db.count(doctype)
			for number in ("Missing-Scan", record.name, " "):
				self.assertEqual(get_serial_batch_scan(self.item.name, number, doctype), {})
			self.assertEqual(get_serial_batch_scan(self.other_item.name, "Scan-001", doctype), {})
			self.assertEqual(frappe.db.count(doctype), count)

	def test_scan_lookup_requires_item_permission(self):
		for doctype in ("Serial No", "Batch"):
			self.make_number(doctype, "Scan-001")
			with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
				get_serial_batch_scan(self.item.name, "Scan-001", doctype)

	def test_scan_lookup_works_without_master_read_permission(self):
		batch = self.make_number("Batch", "Scan-001")
		user = frappe.get_doc(
			doctype="User",
			email="identity-scan-reader@example.com",
			first_name="Scan Reader",
			send_welcome_email=0,
			roles=[{"role": "Sales User"}],
		).insert()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Batch", "read"))
			self.assertEqual(get_serial_batch_scan(self.item.name, "Scan-001", "Batch")["name"], batch.name)
			self.assertEqual(get_serial_batch_scan(self.item.name, "Missing-Scan", "Batch"), {})
		self.assertFalse(frappe.db.exists("Batch", {"item": self.item.name, "batch_id": "Missing-Scan"}))

	def test_number_lookup_works_without_master_read_permission(self):
		batch = self.make_number("Batch", "Titled-001")
		foreign = self.make_number("Batch", "Foreign-001", self.other_item.name)
		user = self.make_role_user("identity-title-reader@example.com", "Sales User")
		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Batch", "read"))
			self.assertEqual(
				get_serial_batch_numbers(self.item.name, "Batch", [batch.name, foreign.name]),
				{batch.name: "Titled-001"},
			)
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_serial_batch_numbers(self.item.name, "Batch", [batch.name])

	def test_sql_characters_in_physical_numbers(self):
		for doctype in ("Serial No", "Batch"):
			number = "LOT-'OR'1'='1"
			doc = self.make_number(doctype, number)
			self.assertEqual(SerialBatchIdentity(doctype).resolve(self.item.name, [number]), [doc.name])

	def test_same_number_for_different_items(self):
		for doctype in ("Serial No", "Batch"):
			first = self.make_number(doctype, "Shared-001")
			second = self.make_number(doctype, "Shared-001", self.other_item.name)
			identity = SerialBatchIdentity(doctype)
			self.assertNotEqual(first.name, second.name)
			self.assertEqual(identity.resolve(self.item.name, ["SHARED-001"]), [first.name])
			self.assertEqual(identity.resolve(self.other_item.name, ["shared-001"]), [second.name])

	def test_returned_serial_text_resolves_by_item(self):
		serials = [
			self.make_number("Serial No", "Returned-001", item.name) for item in (self.item, self.other_item)
		]
		parent = frappe._dict(doctype="POS Invoice", name="Original-Invoice")
		child = frappe._dict(doctype="POS Invoice Item", name="Original-Row")
		for serial in serials:
			row = frappe._dict(item_code=serial.item_code, serial_no="returned-001")
			with self.set_user("Guest"), patch("frappe.get_all", return_value=[row]):
				self.assertEqual(get_returned_serial_nos(child, parent), [serial.name])
			self.assertEqual(row.serial_no, "returned-001")

	def test_returned_serial_lookup_uses_the_selected_bundle(self):
		parent = frappe._dict(doctype="Purchase Receipt", name="Original-Receipt")
		child = frappe._dict(doctype="Purchase Receipt Item", name="Original-Row")
		row = frappe._dict(
			item_code=self.item.name,
			serial_no="Ignored-Text",
			rejected_serial_no="Ignored-Text",
			serial_and_batch_bundle="Accepted-Bundle",
			rejected_serial_and_batch_bundle="Rejected-Bundle",
		)
		for field, bundle in (
			("serial_and_batch_bundle", "Accepted-Bundle"),
			("rejected_serial_and_batch_bundle", "Rejected-Bundle"),
		):
			serial = self.make_number("Serial No", bundle)
			with (
				self.subTest(field=field),
				patch("frappe.get_all", return_value=[row]),
				patch(
					"erpnext.stock.serial_batch_bundle.get_serial_nos", return_value=[serial.name]
				) as lookup,
			):
				self.assertEqual(get_returned_serial_nos(child, parent, field), [serial.name])
				lookup.assert_called_once_with([bundle])

	def test_return_validation_resolves_original_serial_text_by_item(self):
		serial = self.make_number("Serial No", "Returned-001")
		other_serial = self.make_number("Serial No", "Returned-001", self.other_item.name)
		original = frappe._dict(item_code=self.item.name, serial_no="returned-001")
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=self.item.name,
			has_serial_no=1,
			voucher_type="Delivery Note",
			returned_against="Original-Row",
			entries=[{"serial_no": serial.name}],
		)
		with patch.object(bundle, "get_orignal_document_data", return_value=[original]):
			bundle.validate_serial_and_batch_no_for_returned()
			bundle.item_code = self.other_item.name
			bundle.entries[0].serial_no = other_serial.name
			with self.assertRaisesRegex(frappe.ValidationError, "Returned-001.*not part") as error:
				bundle.validate_serial_and_batch_no_for_returned()
		self.assertNotIn(other_serial.name, str(error.exception))
		self.assertEqual(original.serial_no, "returned-001")
		self.assertEqual(bundle.entries[0].serial_no, other_serial.name)

	def test_return_validation_prefers_bundle_and_reports_invalid_physical_numbers(self):
		serial = self.make_number("Serial No", "Returned-001")
		invalid_serial = self.make_number("Serial No", "Other-002")
		original = frappe._dict(
			item_code=self.item.name, serial_no="Ignored-Text", serial_and_batch_bundle="Original-Bundle"
		)
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=self.item.name,
			has_serial_no=1,
			voucher_type="Purchase Receipt",
			returned_against="Original-Row",
			entries=[{"serial_no": serial.name}],
		)
		with (
			patch.object(bundle, "get_orignal_document_data", return_value=[original]),
			patch(
				"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_nos_from_bundle",
				return_value=[serial.name],
			),
		):
			bundle.validate_serial_and_batch_no_for_returned()
			bundle.entries[0].serial_no = invalid_serial.name
			with self.assertRaisesRegex(frappe.ValidationError, "Other-002.*not part") as error:
				bundle.validate_serial_and_batch_no_for_returned()
		self.assertNotIn(invalid_serial.name, str(error.exception))
		self.assertNotIn(serial.serial_no, str(error.exception))
		self.assertEqual(bundle.entries[0].serial_no, invalid_serial.name)

	def test_reconciliation_balance_returns_physical_serials_in_order(self):
		item = make_item("_Identity Serial Only", {"has_serial_no": 1})
		first = self.make_number("Serial No", "Balance-001", item.name)
		second = self.make_number("Serial No", "Balance-002", item.name)
		self.make_number("Serial No", "Balance-001", self.other_item.name)
		serial_ids = f"{second.name}\n{first.name}"
		with patch(
			"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance",
			return_value=(2, 100, serial_ids),
		):
			balance = get_stock_balance_for(item.name, "_Test Warehouse - _TC", "2026-01-01", "12:00:00")
		self.assertEqual(balance["serial_nos"], "Balance-002\nBalance-001")
		self.assertEqual(balance["qty"], 2)
		self.assertEqual(balance["rate"], 100)

	def test_reconciliation_fetch_items_populates_physical_serial_text(self):
		item = make_item("_Identity Serial Only", {"has_serial_no": 1})
		serial = self.make_number("Serial No", "Fetch-001", item.name)
		with (
			patch(
				"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_itemwise_batch",
				return_value={},
			),
			patch(
				"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance",
				return_value=(1, 100, serial.name),
			) as balance,
		):
			args = {
				"warehouse": "_Test Warehouse - _TC",
				"posting_date": "2026-01-01",
				"posting_time": "12:00:00",
				"company": "_Test Company",
				"item_code": item.name,
				"ignore_empty_stock": True,
			}
			(row,) = get_items(**args)
			self.assertEqual(row["serial_no"], "Fetch-001")
			self.assertEqual(row["current_serial_no"], "Fetch-001")
			self.assertEqual(row["qty"], 1)
			self.assertEqual(row["valuation_rate"], 100)
			balance.return_value = (0, 0, None)
			self.assertEqual(get_items(**args), [])

	def test_stock_ledger_serial_balance_keeps_internal_ids(self):
		first = self.make_number("Serial No", "Ledger-001")
		second = self.make_number("Serial No", "Ledger-002")
		sle = frappe._dict(
			item_code=self.item.name,
			warehouse="_Test Warehouse - _TC",
			posting_date="2026-01-01",
			posting_time="12:00:00",
			serial_no=second.name,
			actual_qty=1,
		)
		available = {}
		with patch(
			"erpnext.stock.report.stock_ledger.stock_ledger.get_available_serial_nos",
			return_value=[frappe._dict(serial_no=first.name), frappe._dict(serial_no=second.name)],
		) as lookup:
			update_available_serial_nos(available, sle)
			self.assertEqual(available[(sle.item_code, sle.warehouse)], [first.name])
			self.assertEqual(sle.balance_serial_no, first.name)
			self.assertEqual(lookup.call_args.args[0].warehouse, sle.warehouse)
			self.assertEqual(lookup.call_args.args[0].posting_date, sle.posting_date)
			self.assertEqual(lookup.call_args.args[0].posting_time, sle.posting_time)
			self.assertEqual(lookup.call_args.args[0].ignore_warehouse, 1)

	def test_reconciliation_current_bundle_resolves_only_existing_item_serials(self):
		self.make_number("Serial No", "Current-001", self.other_item.name)
		doc = frappe.get_doc(
			doctype="Stock Reconciliation",
			company="_Test Company",
			posting_date="2026-01-01",
			posting_time="12:00:00",
			items=[
				{
					"item_code": self.item.name,
					"warehouse": "_Test Warehouse - _TC",
					"use_serial_batch_fields": 1,
					"current_qty": 1,
					"current_serial_no": "current-001",
				}
			],
		)
		row = doc.items[0]
		with (
			patch("erpnext.stock.serial_batch_bundle.SerialBatchCreation") as creation,
			patch.object(row, "db_set"),
		):
			with self.assertRaisesRegex(frappe.ValidationError, "current-001.*does not exist"):
				doc.make_bundle_for_current_qty()
			creation.assert_not_called()
			self.assertFalse(
				frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "Current-001"})
			)
			serial = self.make_number("Serial No", "Current-001")
			creation.return_value.make_serial_and_batch_bundle.return_value = frappe._dict(name="Test-Bundle")
			doc.make_bundle_for_current_qty()
			self.assertEqual(creation.call_args.args[0]["serial_nos"], [serial.name])
			self.assertEqual(creation.call_args.args[0]["type_of_transaction"], "Outward")
			self.assertEqual(creation.call_args.args[0]["qty"], -1)
		self.assertEqual(row.current_serial_and_batch_bundle, "Test-Bundle")

	def test_reconciliation_excludes_unchanged_serial_ids(self):
		kept = self.make_number("Serial No", "Keep-001")
		removed = self.make_number("Serial No", "Remove-002")
		self.make_number("Serial No", "Keep-001", self.other_item.name)
		row = frappe._dict(item_code=self.item.name, current_serial_no="Keep-001\nRemove-002")
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=self.item.name,
			has_serial_no=1,
			voucher_type="Stock Reconciliation",
			voucher_detail_no="Reconciliation-Row",
			entries=[{"serial_no": kept.name}, {"serial_no": removed.name}],
		)
		with patch(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_stock_reco_details",
			return_value=row,
		):
			for numbers, expected in (
				("keep-001\nNew-003", {removed.name}),
				("", {kept.name, removed.name}),
			):
				with self.subTest(numbers=numbers):
					row.serial_no = numbers
					serials, batches = bundle.get_serial_nos_for_validate()
					self.assertEqual(set(serials), expected)
					self.assertEqual(batches, [])
					self.assertEqual(row.serial_no, numbers)
		self.assertEqual(row.current_serial_no, "Keep-001\nRemove-002")
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "New-003"}))

	def test_pick_list_allocation_shows_numbers_and_preserves_remaining_ids(self):
		first = self.make_number("Serial No", "Pick-001")
		second = self.make_number("Serial No", "Pick-002")
		self.make_number("Serial No", "Pick-001", self.other_item.name)
		item = frappe._dict(item_code=self.item.name, stock_qty=1, qty=1, conversion_factor=1, uom="Nos")
		locations = {
			self.item.name: [
				frappe._dict(warehouse="_Test Warehouse - _TC", qty=2, serial_nos=[second.name, first.name])
			]
		}
		selected = get_items_with_location_and_quantity(item, locations, docstatus=0)
		self.assertEqual(selected[0].serial_no, "Pick-002")
		self.assertEqual(locations[self.item.name][0].serial_nos, [first.name])
		selected = get_items_with_location_and_quantity(item, locations, docstatus=0)
		self.assertEqual(selected[0].serial_no, "Pick-001")
		self.assertEqual(locations[self.item.name], [])

	def test_pick_list_validates_physical_serials_for_item_and_warehouse(self):
		serial = self.make_number("Serial No", "Pick-<001>")
		other = self.make_number("Serial No", "Pick-<001>", self.other_item.name)
		serial.db_set("warehouse", "_Test Warehouse - _TC")
		other.db_set("warehouse", "_Test Warehouse 1 - _TC")
		doc = frappe.get_doc(
			doctype="Pick List",
			locations=[
				{"item_code": self.item.name, "serial_no": "pick-<001>", "warehouse": serial.warehouse}
			],
		)
		doc.check_serial_no_status()
		doc.locations[0].warehouse = other.warehouse
		with self.assertRaises(frappe.ValidationError) as error:
			doc.check_serial_no_status()
		self.assertIn("pick-&lt;001&gt;", str(error.exception))
		self.assertNotIn(serial.name, str(error.exception))
		self.assertEqual(doc.locations[0].serial_no, "pick-<001>")

	def test_pick_list_combines_existing_text_and_bundle_serial_ids(self):
		first = self.make_number("Serial No", "Pick-001")
		second = self.make_number("Serial No", "Pick-002")
		third = self.make_number("Serial No", "Pick-003")
		warehouse = "_Test Warehouse - _TC"
		frappe.get_doc(
			doctype="Serial and Batch Entry",
			parent="Picked-Bundle",
			parenttype="Serial and Batch Bundle",
			parentfield="entries",
			serial_no=second.name,
			qty=1,
		).db_insert()
		doc = frappe.get_doc(
			doctype="Pick List",
			locations=[
				{
					"item_code": self.item.name,
					"warehouse": warehouse,
					"serial_no": "PICK-003",
					"picked_qty": 1,
					"stock_qty": 1,
				}
			],
		)
		rows = [
			frappe._dict(item_code=self.item.name, warehouse=warehouse, serial_no="pick-001", picked_qty=1),
			frappe._dict(
				item_code=self.item.name,
				warehouse=warehouse,
				serial_and_batch_bundle="Picked-Bundle",
				serial_no="Ignored-Text",
				picked_qty=1,
			),
		]
		with patch.object(doc, "_get_pick_list_items", return_value=rows):
			picked = doc.get_picked_items_details([frappe._dict(item_code=self.item.name)])
		self.assertEqual(picked[self.item.name][warehouse].serial_no, [first.name, second.name, third.name])
		self.assertEqual(picked[self.item.name][warehouse].picked_qty, 3)
		self.assertEqual(doc.locations[0].serial_no, "PICK-003")

	def test_pick_list_bundle_creation_resolves_text_without_changing_row(self):
		serial = self.make_number("Serial No", "Pick-001")
		self.make_number("Serial No", "Pick-001", self.other_item.name)
		batch = self.make_number("Batch", "Pick-Batch")
		doc = frappe.get_doc(
			doctype="Pick List",
			company="_Test Company",
			locations=[
				{
					"item_code": self.item.name,
					"serial_no": "pick-001",
					"batch_no": batch.name,
					"stock_qty": 1,
					"use_serial_batch_fields": 1,
					"warehouse": "_Test Warehouse - _TC",
				}
			],
		)
		with (
			patch("erpnext.stock.doctype.pick_list.pick_list.SerialBatchCreation") as creation,
			patch.object(doc.locations[0], "db_set"),
		):
			creation.return_value.make_serial_and_batch_bundle.return_value = frappe._dict(
				name="Picked-Bundle"
			)
			doc.make_bundle_using_old_serial_batch_fields()
		self.assertEqual(creation.call_args.args[0]["serial_nos"], [serial.name])
		self.assertEqual(creation.call_args.args[0]["batches"], {batch.name: 1})
		self.assertEqual(doc.locations[0].serial_no, "pick-001")
		self.assertEqual(doc.locations[0].batch_no, batch.name)

	def test_pick_list_batch_messages_and_availability_show_physical_number(self):
		batch = self.make_number("Batch", "Pick-Batch & Lot")
		batch.db_set("expiry_date", frappe.utils.add_days(frappe.utils.nowdate(), -1))
		doc = frappe.get_doc(
			doctype="Pick List",
			name="Identity-Pick-List",
			status="Open",
			locations=[
				{
					"item_code": self.item.name,
					"warehouse": "_Test Warehouse - _TC",
					"batch_no": batch.name,
					"picked_qty": 1,
					"stock_qty": 1,
				}
			],
		)
		doc.db_insert()
		doc.locations[0].db_insert()
		with self.assertRaises(frappe.ValidationError) as error:
			doc.validate_expired_batches()
		self.assertIn("Pick-Batch &amp; Lot", str(error.exception))
		self.assertNotIn(batch.name, str(error.exception))
		with (
			patch("erpnext.stock.doctype.batch.batch.get_batch_qty", return_value=0),
			self.assertRaises(frappe.ValidationError) as error,
		):
			doc.validate_stock_qty()
		self.assertIn("Pick-Batch &amp; Lot", str(error.exception))
		self.assertNotIn(batch.name, str(error.exception))
		holders = get_pick_list_holders([self.item.name])
		self.assertEqual(len(holders), 1)
		self.assertEqual(holders[0].batch_no, batch.name)
		self.assertEqual(holders[0].batch_id, "Pick-Batch & Lot")
		self.assertEqual(holders[0].holding_qty, 1)

	def test_landed_cost_updates_serial_rates_using_item_and_physical_number(self):
		first = self.make_number("Serial No", "Receipt-001")
		second = self.make_number("Serial No", "Receipt-002")
		other = self.make_number("Serial No", "Receipt-001", self.other_item.name)
		receipt = frappe.get_doc(
			doctype="Purchase Receipt",
			items=[
				{
					"item_code": self.item.name,
					"serial_no": "receipt-001\nRECEIPT-002",
					"valuation_rate": 25,
				},
				{"item_code": self.other_item.name, "serial_no": "RECEIPT-001", "valuation_rate": 40},
			],
		)
		voucher = frappe.get_doc(doctype="Landed Cost Voucher")

		voucher.update_rate_in_serial_no_for_non_asset_items(receipt)

		self.assertEqual(first.reload().purchase_rate, 25)
		self.assertEqual(second.reload().purchase_rate, 25)
		self.assertEqual(other.reload().purchase_rate, 40)
		self.assertEqual(receipt.items[0].serial_no, "receipt-001\nRECEIPT-002")
		self.assertEqual(receipt.items[1].serial_no, "RECEIPT-001")

	def test_delivered_reservations_resolve_physical_serial_text_by_item(self):
		first = self.make_number("Serial No", "Delivered-001")
		second = self.make_number("Serial No", "Delivered-002")
		self.make_number("Serial No", "Delivered-001", self.other_item.name)
		batch = self.make_number("Batch", "Delivered-Batch")
		row = frappe._dict(
			item_code=self.item.name,
			serial_no="delivered-002\nDELIVERED-001",
			batch_no=batch.name,
			stock_qty=-2,
		)
		self.assertEqual(
			get_delivered_serial_batch_for_reservation(row),
			([second.name, first.name], {batch.name: 2}),
		)
		self.assertEqual(row.serial_no, "delivered-002\nDELIVERED-001")
		self.assertEqual(row.batch_no, batch.name)

	def test_delivered_reservations_prefer_bundle_ids(self):
		serial = self.make_number("Serial No", "Delivered-001")
		batch = self.make_number("Batch", "Delivered-Batch")
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=self.item.name,
			entries=[{"serial_no": serial.name, "batch_no": batch.name, "qty": -1}],
		)
		row = frappe._dict(
			item_code=self.item.name,
			serial_and_batch_bundle="Delivered-Bundle",
			serial_no="Different-Selection",
		)
		with patch("frappe.get_doc", return_value=bundle) as lookup:
			self.assertEqual(
				get_delivered_serial_batch_for_reservation(row), ([serial.name], {batch.name: 1})
			)
		lookup.assert_called_once_with("Serial and Batch Bundle", "Delivered-Bundle")
		self.assertEqual(bundle.entries[0].serial_no, serial.name)

	def test_serial_filter_uses_each_rows_item_and_physical_number(self):
		selected = self.make_number("Serial No", "Selected-001")
		other = self.make_number("Serial No", "Selected-001", self.other_item.name)
		available = self.make_number("Serial No", "Available-002")
		for table, item_field in (("items", "item_code"), ("supplied_items", "rm_item_code")):
			with self.subTest(table=table):
				row = frappe._dict({item_field: self.item.name, "serial_no": "SELECTED-001\nselected-001"})
				doc = frappe._dict({table: [row]})
				serial_ids = [available.name, other.name, selected.name]
				self.assertEqual(
					get_filtered_serial_nos(serial_ids, doc, table), [available.name, other.name]
				)
				self.assertEqual(row.serial_no, "SELECTED-001\nselected-001")

	def test_serial_filter_does_not_interpret_physical_numbers_as_ids(self):
		first = self.make_number("Serial No", "Selected-001")
		second = self.make_number("Serial No", first.name)
		doc = frappe._dict(items=[{"item_code": self.item.name, "serial_no": first.name}])
		self.assertEqual(get_filtered_serial_nos([first.name, second.name], doc), [first.name])

	def test_sales_automatic_selection_returns_physical_serial_text(self):
		selected = self.make_number("Serial No", "Selected-001")
		first = self.make_number("Serial No", "Automatic-001")
		second = self.make_number("Serial No", "Automatic-002")
		self.make_number("Serial No", "Automatic-001", self.other_item.name)
		batch = self.make_number("Batch", "Automatic-Batch")
		for doctype in ("Delivery Note", "Sales Invoice", "POS Invoice"):
			for has_batch_no in (0, 1):
				with self.subTest(doctype=doctype, has_batch_no=has_batch_no):
					ctx = frappe._dict(
						doctype=doctype,
						item_code=self.item.name,
						warehouse="_Test Warehouse - _TC",
						update_stock=1,
						batch_no=batch.name if has_batch_no else None,
					)
					out = frappe._dict(
						item_code=self.item.name,
						warehouse=ctx.warehouse,
						has_serial_no=1,
						has_batch_no=has_batch_no,
						stock_qty=1,
					)
					doc = frappe._dict(items=[{"item_code": self.item.name, "serial_no": "SELECTED-001"}])
					with patch(
						"erpnext.stock.doctype.serial_no.serial_no.get_serial_nos_for_outward",
						return_value=[selected.name, first.name, second.name],
					) as lookup:
						update_stock(ctx, out, doc)
					self.assertEqual(out.serial_no, "Automatic-001")
					self.assertEqual(out.stock_qty, 1)
					self.assertEqual(doc["items"][0]["serial_no"], "SELECTED-001")
					self.assertEqual(lookup.call_args.args[0].item_code, self.item.name)
					if has_batch_no:
						self.assertEqual(lookup.call_args.args[0].batches, [batch.name])

	def test_supplied_item_automatic_selection_fills_physical_serial_text(self):
		first = self.make_number("Serial No", "Automatic-001")
		second = self.make_number("Serial No", "Automatic-002")
		self.make_number("Serial No", "Automatic-001", self.other_item.name)
		doc = frappe.get_doc(
			doctype="Subcontracting Receipt",
			supplier_warehouse="_Test Warehouse - _TC",
			supplied_items=[
				{"rm_item_code": self.item.name, "consumed_qty": 2, "use_serial_batch_fields": 1}
			],
		)
		available = [frappe._dict(serial_no=second.name), frappe._dict(serial_no=first.name)]
		with patch(
			"erpnext.controllers.subcontracting_controller.get_available_serial_nos", return_value=available
		) as lookup:
			doc.set_batch_for_supplied_items()

		self.assertEqual(doc.supplied_items[0].serial_no, "Automatic-002\nAutomatic-001")
		self.assertEqual(doc.supplied_items[0].consumed_qty, 2)
		self.assertEqual([serial.serial_no for serial in available], [second.name, first.name])
		self.assertEqual(lookup.call_args.args[0].item_code, self.item.name)
		self.assertEqual(lookup.call_args.args[0].warehouse, doc.supplier_warehouse)

	def test_supplier_availability_deducts_serials_across_text_and_bundles(self):
		consumed = self.make_number("Serial No", "Supplier-001")
		remaining = self.make_number("Serial No", "Supplier-002")
		self.make_number("Serial No", "Supplier-001", self.other_item.name)
		warehouse = "_Test Warehouse - _TC"
		key = (self.item.name, "Finished Item", "Subcontracting Order")
		for transfer_text, receipt_text in ((True, True), (True, False), (False, True)):
			with self.subTest(transfer_text=transfer_text, receipt_text=receipt_text):
				doc = frappe.get_doc(doctype="Subcontracting Receipt", supplier_warehouse=warehouse)
				doc.subcontract_orders = [key[2]]
				doc.available_materials = {}
				transfer = frappe._dict(
					rm_item_code=self.item.name,
					main_item_code=key[1],
					subcontracting_order=key[2],
					voucher_no="Transfer",
					t_warehouse=warehouse,
					qty=2,
					serial_no="supplier-001\nSUPPLIER-002" if transfer_text else None,
				)
				receipt = frappe._dict(
					rm_item_code=self.item.name,
					main_item_code=key[1],
					reference_name="Receipt Row",
					voucher_no="Receipt",
					consumed_qty=1,
					serial_no="SUPPLIER-001" if receipt_text else None,
				)
				transfer_bundles = (
					{}
					if transfer_text
					else {
						(self.item.name, key[1], warehouse, "Transfer"): frappe._dict(
							serial_nos=[consumed.name, remaining.name]
						)
					}
				)
				receipt_bundles = (
					{}
					if receipt_text
					else {
						(self.item.name, key[1], warehouse, "Receipt"): frappe._dict(
							serial_nos=[consumed.name]
						)
					}
				)
				with (
					patch.object(
						doc, "_SubcontractingController__get_transferred_items", return_value=[transfer]
					),
					patch.object(
						doc,
						"_SubcontractingController__get_received_items",
						return_value=[frappe._dict(name="Receipt Row", subcontracting_order=key[2])],
					),
					patch.object(
						doc, "_SubcontractingController__get_consumed_items", return_value=[receipt]
					),
					patch(
						"erpnext.controllers.subcontracting_controller.get_voucher_wise_serial_batch_from_bundle",
						side_effect=[transfer_bundles, receipt_bundles],
					),
					patch("erpnext.deprecation_dumpster.deprecation_warning"),
				):
					doc.get_available_materials()
				self.assertEqual(doc.available_materials[key].serial_no, [remaining.name])
				self.assertEqual(doc.available_materials[key].qty, 1)
				self.assertEqual(transfer.serial_no, "supplier-001\nSUPPLIER-002" if transfer_text else None)
				self.assertEqual(receipt.serial_no, "SUPPLIER-001" if receipt_text else None)

	def test_supplied_item_serial_text_keeps_allocation_order_and_quantity(self):
		first = self.make_number("Serial No", "Supplied-001")
		second = self.make_number("Serial No", "Supplied-002")
		remaining = self.make_number("Serial No", "Supplied-003")
		self.make_number("Serial No", "Supplied-001", self.other_item.name)
		doc = frappe.get_doc(doctype="Subcontracting Receipt")
		item = frappe._dict(item_code="Finished Item", subcontracting_order="Subcontracting Order")
		key = (self.item.name, item.item_code, item.subcontracting_order)
		doc.available_materials = {key: {"serial_no": [second.name, first.name, remaining.name]}}
		row = frappe._dict(rm_item_code=self.item.name, consumed_qty=2)

		doc._SubcontractingController__set_serial_nos(item, row)

		self.assertEqual(row.serial_no, "Supplied-002\nSupplied-001")
		self.assertEqual(row.consumed_qty, 2)
		self.assertEqual(doc.available_materials[key]["serial_no"], [remaining.name])
		next_row = frappe._dict(rm_item_code=self.item.name, consumed_qty=1)

		doc._SubcontractingController__set_serial_nos(item, next_row)

		self.assertEqual(next_row.serial_no, "Supplied-003")
		self.assertEqual(doc.available_materials[key]["serial_no"], [])
		self.assertEqual(row.serial_no, "Supplied-002\nSupplied-001")

	def test_subcontracting_return_stock_entry_uses_physical_serial_text(self):
		first = self.make_number("Serial No", "Return-001")
		second = self.make_number("Serial No", "Return-002")
		self.make_number("Serial No", "Return-001", self.other_item.name)
		batch = self.make_number("Batch", "Return-Batch")
		materials = frappe._dict(
			serial_no=[second.name, first.name],
			sco_rm_details=["Order-Row"],
			item_details={
				"rm_item_code": self.item.name,
				"main_item_code": "Finished Item",
				"rate": 10,
				"s_warehouse": "_Test Warehouse - _TC",
				"t_warehouse": "_Test Warehouse 1 - _TC",
			},
		)
		doc = frappe.get_doc(doctype="Stock Entry")

		add_items_in_ste(doc, materials, 2, ["Order-Row"], batch_no=batch.name)

		row = doc.items[0]
		self.assertEqual(row.item_code, self.item.name)
		self.assertEqual(row.serial_no, "Return-002\nReturn-001")
		self.assertEqual(row.batch_no, batch.name)
		self.assertEqual(row.qty, 2)
		self.assertEqual(row.sco_rm_detail, "Order-Row")
		self.assertEqual(row.s_warehouse, "_Test Warehouse 1 - _TC")
		self.assertEqual(row.t_warehouse, "_Test Warehouse - _TC")
		self.assertEqual(materials.serial_no, [second.name, first.name])

	def test_subcontracting_errors_link_physical_numbers_to_their_records(self):
		for doctype in ("Serial No", "Batch"):
			record = self.make_number(doctype, "Unreserved-<001>")
			doc = frappe.get_doc(
				doctype="Stock Entry",
				purpose="Subcontracting Delivery",
				subcontracting_inward_order="_Identity Inward Order",
				items=[
					{
						"item_code": self.item.name,
						"serial_no": "Unreserved-<001>" if doctype == "Serial No" else None,
						"batch_no": record.name if doctype == "Batch" else None,
					}
				],
			)
			with (
				self.subTest(doctype=doctype),
				patch.object(doc, "get_serial_nos_and_batches_from_sres", return_value=([], {})),
				self.assertRaisesRegex(
					frappe.ValidationError, "not a part of the linked Subcontracting Inward Order"
				) as error,
			):
				doc.validate_serial_batch_for_return_or_delivery()
			message = str(error.exception)
			self.assertIn(f'href="{get_url_to_form(doctype, record.name)}"', message)
			self.assertIn(">Unreserved-&lt;001&gt;</a>", message)
			self.assertNotIn(f">{record.name}</a>", message)
			self.assertNotIn("Unreserved-<001>", message)

	def test_subcontracting_fields_show_numbers_and_keep_bundle_inputs_as_ids(self):
		first = self.make_number("Serial No", "Subcontracting-001")
		second = self.make_number("Serial No", "Subcontracting-002")
		batch = self.make_number("Batch", "Subcontracting-Batch")
		serial_ids = [second.name, first.name]
		batches = {batch.name: 2}
		for purpose in (
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
			"Subcontracting Return",
		):
			doc = frappe.get_doc(
				doctype="Stock Entry",
				purpose=purpose,
				items=[
					{
						"name": "Subcontracting-Row",
						"item_code": self.item.name,
						"scio_detail": "Subcontracting-Order-Row",
						"use_serial_batch_fields": 1,
					}
				],
			)
			service = StockEntrySABB(doc)
			with (
				self.subTest(purpose=purpose),
				patch.object(
					service, "get_serial_nos_and_batches_from_sres", return_value=(serial_ids, batches)
				) as lookup,
			):
				self.assertEqual(
					service.get_serial_batch_fields_for_subcontracting_inward(),
					({"Subcontracting-Row": serial_ids}, {"Subcontracting-Row": batches}),
				)
				row = doc.items[0]
				self.assertEqual(row.serial_no, "Subcontracting-002\nSubcontracting-001")
				self.assertEqual(row.batch_no, batch.name)
				lookup.assert_called_once_with(
					"Subcontracting-Order-Row", only_pending=purpose != "Subcontracting Return"
				)
				row.serial_no = "Manual-Selection"
				service.get_serial_batch_fields_for_subcontracting_inward()
				self.assertEqual(row.serial_no, "Manual-Selection")

	def test_subcontracting_serial_list_resolves_physical_text_by_item(self):
		first = self.make_number("Serial No", "Subcontracting-001")
		second = self.make_number("Serial No", "Subcontracting-002")
		self.make_number("Serial No", "Subcontracting-001", self.other_item.name)
		batch = self.make_number("Batch", "Subcontracting-Batch")
		row = frappe._dict(
			item_code=self.item.name,
			serial_no="subcontracting-002\nSUBCONTRACTING-001",
			batch_no=batch.name,
		)
		self.assertEqual(get_serial_batch_list_from_item(row), ([second.name, first.name], [batch.name]))
		self.assertEqual(row.serial_no, "subcontracting-002\nSUBCONTRACTING-001")
		self.assertEqual(row.batch_no, batch.name)

		row.serial_no = first.name
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			get_serial_batch_list_from_item(row)

	def test_subcontracting_serial_list_prefers_bundle_ids(self):
		serial = self.make_number("Serial No", "Subcontracting-001")
		self.make_number("Serial No", serial.name)
		batch = self.make_number("Batch", "Subcontracting-Batch")
		frappe.get_doc(
			doctype="Serial and Batch Entry",
			parent="_Identity Subcontracting Bundle",
			parenttype="Serial and Batch Bundle",
			parentfield="entries",
			serial_no=serial.name,
			batch_no=batch.name,
		).db_insert()
		row = frappe._dict(
			item_code=self.item.name,
			serial_and_batch_bundle="_Identity Subcontracting Bundle",
			serial_no="Ignored-Text",
			batch_no="Ignored-Batch",
		)
		self.assertEqual(get_serial_batch_list_from_item(row), ([serial.name], [batch.name]))
		self.assertEqual(row.serial_no, "Ignored-Text")
		self.assertEqual(row.batch_no, "Ignored-Batch")

	def test_reserved_materials_keep_ids_and_supply_physical_serial_text(self):
		masters = [
			(
				self.make_number("Serial No", "Reserved-001", item.name),
				self.make_number("Batch", "Reserved-Batch", item.name),
			)
			for item in (self.item, self.other_item)
		]
		warehouse = "_Test Warehouse - _TC"
		for mode in ("Serial", "Batch", "Combined"):
			voucher = f"_Identity Reserved Materials {mode}"
			for serial, batch in masters:
				reservation = frappe.get_doc(
					doctype="Stock Reservation Entry",
					name=f"{voucher}-{serial.item_code}",
					item_code=serial.item_code,
					warehouse=warehouse,
					voucher_no=voucher,
					docstatus=1,
				)
				reservation.db_insert()
				frappe.get_doc(
					doctype="Serial and Batch Entry",
					parent=reservation.name,
					parenttype="Stock Reservation Entry",
					parentfield="sb_entries",
					serial_no=serial.name if mode != "Batch" else None,
					batch_no=batch.name if mode != "Serial" else None,
					qty=1,
					delivered_qty=0,
				).db_insert()

			with self.subTest(mode=mode):
				entries = {entry.item_code: entry for entry in get_reserved_materials(voucher)}
				doc = frappe.get_doc(doctype="Stock Entry", work_order=voucher)
				materials = StockEntrySABB(doc).get_available_reserved_materials()
				for serial, batch in masters:
					entry = entries[serial.item_code]
					details = materials[(serial.item_code, warehouse)]
					if mode != "Batch":
						self.assertEqual(entry.serial_no, serial.name)
						self.assertEqual(entry.serial_number, serial.serial_no)
						if mode == "Serial":
							self.assertEqual(details.serial_no, [serial.serial_no])
						else:
							self.assertEqual(details.batchwise_sn[batch.name], [serial.serial_no])
					else:
						self.assertFalse(details.serial_no)
						self.assertFalse(details.batchwise_sn)
					if mode != "Serial":
						self.assertEqual(entry.batch_no, batch.name)
						self.assertEqual(details.batch_no, {batch.name: 1})

	def test_available_materials_match_serial_text_and_bundle_ids(self):
		consumed = self.make_number("Serial No", "Material-001")
		remaining = self.make_number("Serial No", "Material-002")
		self.make_number("Serial No", "Material-001", self.other_item.name)
		warehouse = "_Test Warehouse - _TC"
		for bundled_transfer in (False, True):
			transfer = frappe._dict(
				name="Transfer",
				item_code=self.item.name,
				warehouse=warehouse,
				qty=2,
				purpose="Material Transfer for Manufacture",
				serial_no="material-001\nMATERIAL-002",
			)
			consumption = frappe._dict(
				name="Consumption",
				item_code=self.item.name,
				s_warehouse=warehouse,
				qty=1,
				purpose="Manufacture",
				serial_no="MATERIAL-001",
			)
			bundled_row = transfer if bundled_transfer else consumption
			bundled_row.serial_no = "Ignored-Text"
			serial_ids = [consumed.name, remaining.name] if bundled_transfer else [consumed.name]
			bundle_data = {(self.item.name, warehouse, bundled_row.name): {"serial_nos": serial_ids}}
			with (
				self.subTest(bundled_transfer=bundled_transfer),
				patch(
					"erpnext.stock.doctype.stock_entry.services.disassemble._run_stock_entry_query",
					return_value=[transfer, consumption],
				),
				patch(
					"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_voucher_wise_serial_batch_from_bundle",
					return_value=bundle_data,
				),
			):
				materials = get_available_materials("_Identity Work Order")
				available = materials[(self.item.name, warehouse)]
				self.assertEqual(available.serial_nos, [remaining.name])
				self.assertEqual(available.qty, 1)
				self.assertEqual(bundled_row.serial_no, "Ignored-Text")

	def test_disassembly_resolves_source_serial_text_by_item(self):
		first = self.make_number("Serial No", "Disassembly-001")
		second = self.make_number("Serial No", "Disassembly-002")
		self.make_number("Serial No", "Disassembly-001", self.other_item.name)
		source = frappe._dict(item_code=self.item.name, serial_no="disassembly-002\nDISASSEMBLY-001")
		row = frappe._dict(transfer_qty=1)
		service = DisassembleStockEntry(frappe.get_doc(doctype="Stock Entry", purpose="Disassemble"))

		self.assertEqual(service._extract_serial_nos(source, {}, row), [second.name])
		row.transfer_qty = 2
		self.assertEqual(service._extract_serial_nos(source, {}, row), [second.name, first.name])
		self.assertEqual(source.serial_no, "disassembly-002\nDISASSEMBLY-001")

		source.serial_no = "Missing-Disassembly"
		with self.assertRaisesRegex(frappe.ValidationError, "Missing-Disassembly.*does not exist"):
			service._extract_serial_nos(source, {}, row)
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "Missing-Disassembly"})
		)

	def test_disassembly_prefers_source_bundle_ids(self):
		serial = self.make_number("Serial No", "Disassembly-001")
		self.make_number("Serial No", serial.name)
		source = frappe._dict(item_code=self.item.name, serial_no="Unused-Source-Text")
		bundle = {"serial_nos": [serial.name]}
		row = frappe._dict(transfer_qty=1)
		service = DisassembleStockEntry(frappe.get_doc(doctype="Stock Entry", purpose="Disassemble"))

		self.assertEqual(service._extract_serial_nos(source, bundle, row), [serial.name])
		self.assertEqual(bundle["serial_nos"], [serial.name])

	def test_finished_good_validation_matches_physical_numbers_to_work_order(self):
		serial = self.make_number("Serial No", "Finished-001")
		serial.db_set("work_order", "_Identity Work Order")
		other = self.make_number("Serial No", "Finished-002")
		other.db_set("work_order", "_Other Work Order")
		self.make_number("Serial No", "Finished-001", self.other_item.name)
		service = ManufactureStockEntry(frappe._dict(work_order="_Identity Work Order"))
		service._wo_doc = frappe._dict(has_serial_no=1)
		for text, invalid in (
			("finished-001", False),
			("finished-001\nFINISHED-001", False),
			("FINISHED-002", True),
		):
			with self.subTest(text=text):
				row = frappe._dict(item_code=self.item.name, serial_no=text)
				self.assertEqual(service.check_invalid_serial_batch_nos_for_finished_good_item(row), invalid)
				self.assertEqual(row.serial_no, text)

	def test_finished_good_missing_serial_preserves_existing_messages(self):
		service = ManufactureStockEntry(frappe._dict(work_order="_Identity Work Order"))
		service._wo_doc = frappe._dict(has_serial_no=1)
		row = frappe._dict(item_code=self.item.name, serial_no="Missing-Finished-Serial")
		with patch.dict(frappe.flags, {"mute_messages": False}):
			frappe.msgprint(frappe._("Existing notice"))
		messages = frappe.get_message_log()
		for muted in (False, True):
			with self.subTest(muted=muted), patch.dict(frappe.flags, {"mute_messages": muted}):
				self.assertTrue(service.check_invalid_serial_batch_nos_for_finished_good_item(row))
				self.assertEqual(frappe.get_message_log(), messages)
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": row.serial_no})
		)
		with patch.object(
			SerialBatchIdentity, "resolve", side_effect=frappe.ValidationError("Invalid input")
		):
			with self.assertRaisesRegex(frappe.ValidationError, "Invalid input"):
				service.check_invalid_serial_batch_nos_for_finished_good_item(row)

	def test_finished_good_bundle_validation_checks_item_and_keeps_ids(self):
		serials = [
			self.make_number("Serial No", "Finished-001", item.name) for item in (self.item, self.other_item)
		]
		for serial in serials:
			serial.db_set("work_order", "_Identity Work Order")
		service = ManufactureStockEntry(frappe._dict(work_order="_Identity Work Order"))
		service._wo_doc = frappe._dict(has_serial_no=1)
		row = frappe._dict(item_code=self.item.name, serial_and_batch_bundle="_Identity Finished Bundle")
		for serial in serials:
			with patch(
				"erpnext.stock.doctype.stock_entry.services.manufacturing.get_serial_nos_from_bundle",
				return_value=[serial.name],
			):
				self.assertEqual(
					service.check_invalid_serial_batch_nos_for_finished_good_item(row),
					serial.item_code != self.item.name,
				)
		self.assertEqual(row.serial_and_batch_bundle, "_Identity Finished Bundle")

	def test_manufacturing_material_row_uses_physical_numbers_in_selected_order(self):
		serials = [
			self.make_number("Serial No", number)
			for number in ("Material-001", "Material-002", "Material-003")
		]
		self.make_number("Serial No", "Material-001", self.other_item.name)
		serial_ids = [serials[1].name, serials[0].name, serials[2].name]
		available = frappe._dict(serial_nos=serial_ids.copy(), stock_uom="Nos")
		doc = frappe.get_doc(doctype="Stock Entry", purpose="Manufacture", items=[])
		item_args = {"item_code": self.item.name, "qty": 2, "transfer_qty": 2}

		ManufactureStockEntry(doc)._append_with_serial_nos(item_args, available, 2)

		self.assertEqual(len(doc.items), 1)
		row = doc.items[0]
		self.assertEqual(row.serial_no, "Material-002\nMaterial-001")
		self.assertEqual(row.qty, 2)
		self.assertEqual(row.uom, "Nos")
		self.assertEqual(row.use_serial_batch_fields, 1)
		self.assertEqual(available.serial_nos, serial_ids)

	def test_job_card_allocation_uses_physical_numbers_and_excludes_used_serials(self):
		work_order = "_Identity Work Order"
		for number in ("Job-003", "Job-001", "Job-002"):
			self.make_number("Serial No", number).db_set("work_order", work_order)
		self.make_number("Serial No", "Job-000").db_set("work_order", "_Other Work Order")
		self.make_number("Serial No", "Job-000", self.other_item.name).db_set("work_order", work_order)
		for name, operation, number, docstatus in (
			("_Identity Active Job", "Operation-A", "job-001", 0),
			("_Identity Cancelled Job", "Operation-A", "Job-002", 2),
			("_Identity Other Operation", "Operation-B", "Job-003", 0),
		):
			frappe.get_doc(
				doctype="Job Card",
				name=name,
				work_order=work_order,
				operation_id=operation,
				serial_no=number,
				docstatus=docstatus,
			).db_insert()

		wo_doc = frappe._dict(name=work_order, production_item=self.item.name, has_serial_no=1)
		row = frappe._dict(name="Operation-A", job_card_qty=1)
		get_serial_nos_for_job_card(row, wo_doc)
		self.assertEqual(row.serial_no, "Job-002")
		row.job_card_qty = 2
		get_serial_nos_for_job_card(row, wo_doc)
		self.assertEqual(row.serial_no, "Job-002\nJob-003")

	def test_pos_screen_reservations_return_all_physical_numbers_for_item_and_warehouse(self):
		serials = [self.make_number("Serial No", f"POS-Screen-{index:02}") for index in range(21)]
		other_item = self.make_number("Serial No", "POS-Screen-00", self.other_item.name)
		other_warehouse = self.make_number("Serial No", "POS-Other-Warehouse")
		warehouse = "_Test Warehouse - _TC"
		for serial in [*serials, other_item]:
			serial.db_set("warehouse", warehouse)
		other_warehouse.db_set("warehouse", "_Test Warehouse 1 - _TC")
		reserved = [serial.name for serial in [*serials, other_item, other_warehouse]]
		with patch(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_reserved_serial_nos_for_pos",
			return_value=reserved,
		):
			numbers = get_pos_reserved_serial_nos(
				frappe.as_json({"item_code": self.item.name, "warehouse": warehouse})
			)
		self.assertCountEqual(numbers, [serial.serial_no for serial in serials])

	def test_pos_scan_returns_candidates_and_prices_the_selected_item(self):
		serials = [
			self.make_number("Serial No", "POS-Scan", item.name) for item in (self.item, self.other_item)
		]
		warehouse = "_Test Warehouse - _TC"
		with patch(
			"erpnext.selling.page.point_of_sale.point_of_sale.get_stock_availability", return_value=(2, 1, 0)
		):
			result = search_by_term("pos-scan", warehouse, "Standard Selling", self.pos_profile())
			self.assertCountEqual(
				[row["serial_no_id"] for row in result["candidates"]], [serial.name for serial in serials]
			)
			selected = search_by_term(
				"pos-scan", warehouse, "Standard Selling", self.pos_profile(), self.item.name, "Serial No"
			)
		self.assertTrue(selected["barcode_scan"])
		self.assertEqual(len(selected["items"]), 1)
		self.assertEqual(selected["items"][0]["item_code"], self.item.name)
		self.assertEqual(selected["items"][0]["serial_no"], "POS-Scan")

	def test_pos_batch_scan_keeps_the_selected_batch_id(self):
		items = [make_item(f"_Identity POS Batch {suffix}", {"has_batch_no": 1}) for suffix in ("A", "B")]
		batches = [self.make_number("Batch", "POS-Batch", item.name) for item in items]
		result = search_for_serial_or_batch_or_barcode_number("pos-batch", self.pos_profile())
		self.assertCountEqual(
			[row["batch_no"] for row in result["candidates"]], [batch.name for batch in batches]
		)
		selected = search_for_serial_or_batch_or_barcode_number(
			"pos-batch", self.pos_profile(), items[1].name, "Batch"
		)
		self.assertEqual(selected["batch_no"], batches[1].name)
		self.assertEqual(selected["batch_id"], "POS-Batch")

	def test_pos_same_item_scan_requires_record_selection(self):
		serial = self.make_number("Serial No", "POS-Shared")
		self.make_number("Batch", "POS-Shared")
		result = search_for_serial_or_batch_or_barcode_number(
			"pos-shared", self.pos_profile(), self.item.name
		)
		self.assertCountEqual([row["record_type"] for row in result["candidates"]], ["Serial No", "Batch"])
		selected = search_for_serial_or_batch_or_barcode_number(
			"pos-shared", self.pos_profile(), self.item.name, "Serial No"
		)
		self.assertEqual(selected["serial_no_id"], serial.name)
		with self.assertRaisesRegex(frappe.ValidationError, "requires serial numbers"):
			search_for_serial_or_batch_or_barcode_number(
				"pos-shared", self.pos_profile(), self.item.name, "Batch"
			)
		with self.assertRaisesRegex(frappe.ValidationError, "no longer available"):
			search_for_serial_or_batch_or_barcode_number(
				"pos-shared", self.pos_profile(), self.other_item.name, "Serial No"
			)

	def test_pos_candidate_selection_respects_profile_item_groups(self):
		for item in (self.item, self.other_item):
			self.make_number("Serial No", "POS-Scan", item.name)
		self.other_item.db_set("item_group", "_Test Item Group")
		profile = frappe.get_doc("POS Profile", self.pos_profile())
		profile.append("item_groups", {"item_group": self.item.item_group})
		profile.save()
		result = search_for_serial_or_batch_or_barcode_number("POS-Scan", profile.name)
		filter_result_items(result, profile.name)
		self.assertEqual([row["item_code"] for row in result["candidates"]], [self.item.name])

	def test_pos_groups_physical_serials_by_their_items_batches(self):
		first_batch = self.make_number("Batch", "POS-Batch-1")
		second_batch = self.make_number("Batch", "POS-Batch-2")
		for number, batch in (("POS-Serial-1", first_batch), ("POS-Serial-2", second_batch)):
			serial = self.make_number("Serial No", number)
			serial.db_set("batch_no", batch.name)
			self.make_number("Serial No", number, self.other_item.name)
		self.assertEqual(
			get_serials_by_batch(self.item.name, "pos-serial-2\nPOS-SERIAL-1", self.pos_profile()),
			{second_batch.name: ["POS-Serial-2"], first_batch.name: ["POS-Serial-1"]},
		)
		count = frappe.db.count("Serial No")
		with self.assertRaises(frappe.DoesNotExistError):
			get_serials_by_batch(self.item.name, "POS-Missing", self.pos_profile())
		self.assertEqual(frappe.db.count("Serial No"), count)
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_serials_by_batch(self.item.name, "POS-Serial-1", self.pos_profile())

	def test_pos_endpoints_do_not_reach_items_outside_the_profile(self):
		self.make_number("Serial No", "POS-Outside")
		profile = frappe.get_doc("POS Profile", self.pos_profile())
		profile.append("item_groups", {"item_group": "_Test Item Group"})
		profile.save()
		self.item.db_set("item_group", "All Item Groups")
		for call in (
			lambda: search_for_serial_or_batch_or_barcode_number(
				"POS-Outside", profile.name, self.item.name, "Serial No"
			),
			lambda: get_serials_by_batch(self.item.name, "POS-Outside", profile.name),
		):
			with self.subTest(call=call), self.assertRaises(frappe.PermissionError):
				call()
		self.assertEqual(search_for_serial_or_batch_or_barcode_number("POS-Outside", profile.name), {})

	def test_pos_return_checks_the_original_item_and_literal_serial_number(self):
		serial = self.make_number("Serial No", "POS-Return_1")
		self.make_number("Serial No", serial.serial_no, self.other_item.name)
		self.make_number("Serial No", "POS-ReturnX1")
		frappe.get_doc(
			doctype="POS Invoice Item",
			parent="Identity-POS-Sale",
			parenttype="POS Invoice",
			parentfield="items",
			item_code=self.item.name,
			serial_no="pos-return_1",
		).db_insert()
		doc = frappe.get_doc(
			doctype="POS Invoice",
			is_return=1,
			return_against="Identity-POS-Sale",
			items=[{"item_code": self.item.name, "serial_no": "POS-RETURN_1", "qty": -1}],
		)
		doc.validate_return_items_qty()
		self.assertEqual(doc.items[0].serial_no, "POS-RETURN_1")
		for item, number in ((self.other_item.name, serial.serial_no), (self.item.name, "POS-ReturnX1")):
			doc.items[0].item_code = item
			doc.items[0].serial_no = number
			with self.assertRaises(frappe.ValidationError) as error:
				doc.validate_return_items_qty()
			self.assertIn(frappe.utils.escape_html(number), str(error.exception))
			self.assertNotIn(serial.name, str(error.exception))

	def test_pos_return_accepts_bundle_serials_without_changing_references(self):
		serial = self.make_number("Serial No", "POS-Bundled")
		for bundle in ("Identity-POS-Sale-Bundle", "Identity-POS-Return-Bundle"):
			frappe.get_doc(
				doctype="Serial and Batch Entry",
				parent=bundle,
				parenttype="Serial and Batch Bundle",
				parentfield="entries",
				serial_no=serial.name,
				qty=1,
			).db_insert()
		frappe.get_doc(
			doctype="POS Invoice Item",
			parent="Identity-POS-Sale",
			parenttype="POS Invoice",
			parentfield="items",
			item_code=self.item.name,
			serial_and_batch_bundle="Identity-POS-Sale-Bundle",
			serial_no="Ignored-Text",
		).db_insert()
		doc = frappe.get_doc(
			doctype="POS Invoice",
			is_return=1,
			return_against="Identity-POS-Sale",
			items=[
				{
					"item_code": self.item.name,
					"serial_and_batch_bundle": "Identity-POS-Return-Bundle",
					"qty": -1,
				}
			],
		)
		doc.validate_return_items_qty()
		self.assertEqual(doc.items[0].serial_and_batch_bundle, "Identity-POS-Return-Bundle")

	def test_pos_screen_reservation_lookup_requires_item_read_permission(self):
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_pos_reserved_serial_nos({"item_code": self.item.name, "warehouse": "_Test Warehouse - _TC"})

	def test_pos_auto_selection_excludes_reserved_and_selected_serial_ids(self):
		reserved = self.make_number("Serial No", "POS-Reserved")
		selected = self.make_number("Serial No", "POS-Selected")
		available = self.make_number("Serial No", "POS-Available")
		other = self.make_number("Serial No", "POS-Available", self.other_item.name)
		warehouse = "_Test Warehouse - _TC"
		for serial in (reserved, selected, available, other):
			serial.db_set("warehouse", warehouse)
		with patch(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_reserved_serial_nos_for_pos",
			return_value=[reserved.name],
		):
			self.assertEqual(
				auto_fetch_serial_number(
					5,
					self.item.name,
					warehouse,
					for_doctype="POS Invoice",
					exclude_sr_nos=frappe.as_json([selected.name]),
				),
				[available.name],
			)
			self.assertEqual(
				auto_fetch_serial_number(
					5,
					self.item.name,
					warehouse,
					for_doctype="POS Invoice",
					exclude_sr_nos=frappe.as_json([selected.name]),
					as_numbers=True,
				),
				[available.serial_no],
			)

	def test_pos_serial_text_reservations_exclude_returns(self):
		returned = self.make_number("Serial No", "POS-001")
		reserved = self.make_number("Serial No", "POS-002")
		self.make_number("Serial No", "POS-002", self.other_item.name)
		row = frappe._dict(serial_no="pos-001\nPOS-002", parent_docname="POS-Sale", child_docname="POS-Row")
		with (
			patch("frappe.get_all", return_value=[row]),
			patch(
				"erpnext.controllers.sales_and_purchase_return.get_returned_serial_nos",
				return_value=[returned.name],
			),
		):
			self.assertEqual(
				get_reserved_serial_nos_for_pos(frappe._dict(item_code=self.item.name)), [reserved.name]
			)
		self.assertEqual(row.serial_no, "pos-001\nPOS-002")

	def test_pos_does_not_count_both_serial_text_and_bundle(self):
		serial = self.make_number("Serial No", "POS-001")
		row = frappe._dict(
			serial_no="POS-001",
			serial_and_batch_bundle="POS-Bundle",
			parent_docname="POS-Sale",
			child_docname="POS-Row",
		)
		with (
			patch("frappe.get_all", return_value=[row]),
			patch(
				"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_ledgers",
				return_value=[frappe._dict(serial_no=serial.name)],
			),
			patch(
				"erpnext.controllers.sales_and_purchase_return.get_returned_serial_nos",
				return_value=[serial.name],
			),
		):
			self.assertEqual(get_reserved_serial_nos_for_pos(frappe._dict(item_code=self.item.name)), [])

	def test_pos_resale_keeps_the_serial_reserved(self):
		serial = self.make_number("Serial No", "POS-001")
		rows = [
			frappe._dict(serial_no="pos-001", parent_docname=f"POS-Sale-{i}", child_docname=f"POS-Row-{i}")
			for i in range(2)
		]
		with (
			patch("frappe.get_all", return_value=rows),
			patch(
				"erpnext.controllers.sales_and_purchase_return.get_returned_serial_nos",
				side_effect=[[serial.name], []],
			),
		):
			self.assertEqual(
				get_reserved_serial_nos_for_pos(frappe._dict(item_code=self.item.name)), [serial.name]
			)

	def test_duplicate_serial_is_rejected_by_database(self):
		self.check_duplicate("Serial No", "Number-001")

	def test_duplicate_batch_is_rejected_by_database(self):
		self.check_duplicate("Batch", "Number-001")

	def test_serial_case_variant_is_rejected_by_database(self):
		self.check_duplicate("Serial No", "number-001")

	def test_batch_case_variant_is_rejected_by_database(self):
		self.check_duplicate("Batch", "number-001")

	def test_existing_constraints_are_not_recreated(self):
		with (
			patch.object(frappe.db, "add_unique", side_effect=AssertionError("Repeated constraint creation")),
			patch.object(frappe.db, "sql_ddl", side_effect=AssertionError("Repeated constraint creation")),
		):
			for doctype in ("Serial No", "Batch"):
				identity = SerialBatchIdentity(doctype)
				self.assertTrue(frappe.db.has_index(f"tab{doctype}", identity.constraint_name))
				identity.add_unique_constraint()

	def test_other_constraint_errors_are_not_translated(self):
		for doctype in ("Serial No", "Batch"):
			identity = SerialBatchIdentity(doctype)
			error = Exception(f"Duplicate entry 'for key '{identity.constraint_name}'' for key 'other_index'")
			error.diag = frappe._dict(constraint_name="other_index")
			with patch.object(frappe.db, "is_unique_key_violation", return_value=True):
				self.assertIsNone(identity.raise_duplicate(error, self.item.name, "Number-001"))

	def test_bundle_creation_resolves_numbers_without_changing_transaction_text(self):
		serial = self.make_number("Serial No", "Shared-001")
		self.make_number("Serial No", "Shared-001", self.other_item.name)
		doc = self.make_receipt("shared-001")
		row = doc.items[0]
		details = {"item_code": self.item.name, "serial_nos": ["shared-001"]}
		with (
			patch("erpnext.stock.serial_batch_bundle.SerialBatchCreation") as creation,
			patch.object(row, "db_set"),
		):
			creation.return_value.make_serial_and_batch_bundle.return_value = frappe._dict(name="Test-Bundle")
			SerialBatchBundleService(doc).create_serial_batch_bundle(details, row)
			self.assertEqual(creation.call_args.args[0]["serial_nos"], [serial.name])
		self.assertEqual(row.serial_no, "shared-001")
		self.assertEqual(details["serial_nos"], ["shared-001"])

	def test_existing_bundle_comparison_resolves_numbers_and_rejects_duplicates(self):
		first = self.make_number("Serial No", "First-001")
		second = self.make_number("Serial No", "Second-002")
		for serial in (first, second):
			frappe.get_doc(
				{
					"doctype": "Serial and Batch Entry",
					"parent": "Test-Identity-Bundle",
					"parenttype": "Serial and Batch Bundle",
					"parentfield": "entries",
					"serial_no": serial.name,
				}
			).db_insert()
		doc = self.make_receipt("second-002\nFIRST-001")
		row = doc.items[0]
		row.serial_and_batch_bundle = "Test-Identity-Bundle"
		service = SerialBatchBundleService(doc)
		service.validate_serial_nos_and_batches_with_bundle(row)
		self.assertEqual(row.serial_no, "second-002\nFIRST-001")
		row.serial_no = "First-001\nFirst-001"
		with self.assertRaises(frappe.ValidationError):
			service.validate_serial_nos_and_batches_with_bundle(row)

	def test_serialized_batch_validation_uses_item_and_physical_number(self):
		serial = self.make_number("Serial No", "Shared-001")
		other = self.make_number("Serial No", "Shared-001", self.other_item.name)
		batch = self.make_number("Batch", "Batch-001")
		other_batch = self.make_number("Batch", "Batch-001", self.other_item.name)
		wrong_batch = self.make_number("Batch", "Batch-002")
		for record, assigned_batch in ((serial, batch), (other, other_batch)):
			frappe.db.set_value(
				"Serial No",
				record.name,
				{"batch_no": assigned_batch.name, "warehouse": "_Test Warehouse - _TC"},
			)
		doc = self.make_receipt("SHARED-001")
		doc.items[0].batch_no = batch.name
		service = SerialBatchBundleService(doc)
		service.validate_serialized_batch()
		doc.items[0].batch_no = wrong_batch.name
		with self.assertRaisesRegex(frappe.ValidationError, "Shared-001 does not belong to Batch"):
			service.validate_serialized_batch()

	def test_creation_reuses_existing_records_and_groups_case_variants(self):
		serial = self.make_number("Serial No", "Existing-001")
		names = SerialBatchIdentity("Serial No").resolve(
			self.item.name,
			["New-001", "existing-001", "NEW-001"],
			create=True,
			defaults={"company": "_Test Company"},
		)
		self.assertEqual(names, [names[0], serial.name, names[0]])
		created = frappe.get_doc("Serial No", names[0])
		self.assertEqual(created.serial_no, "New-001")
		self.assertNotEqual(created.name, created.serial_no)
		self.assertEqual(created.status, "Inactive")
		self.assertFalse(created.warehouse)

	def test_inward_save_creates_missing_serials_for_the_selected_item(self):
		other = self.make_number("Serial No", "New-001", self.other_item.name)
		doc = self.make_receipt("New-001")
		details = {
			"item_code": self.item.name,
			"serial_nos": ["New-001"],
			"type_of_transaction": "Inward",
		}
		with (
			patch("erpnext.stock.serial_batch_bundle.SerialBatchCreation") as creation,
			patch.object(doc.items[0], "db_set"),
		):
			creation.return_value.make_serial_and_batch_bundle.return_value = frappe._dict(name="Test-Bundle")
			SerialBatchBundleService(doc).create_serial_batch_bundle(details, doc.items[0])
			name = creation.call_args.args[0]["serial_nos"][0]
		self.assertNotEqual(name, other.name)
		serial = frappe.get_doc("Serial No", name)
		self.assertEqual(serial.item_code, self.item.name)
		self.assertEqual(serial.company, doc.company)
		self.assertEqual(serial.status, "Inactive")
		self.assertEqual(doc.items[0].serial_no, "New-001")

	def test_outward_save_does_not_create_missing_serials(self):
		doc = self.make_receipt("Missing-001")
		details = {
			"item_code": self.item.name,
			"serial_nos": ["Missing-001"],
			"type_of_transaction": "Outward",
		}
		count = frappe.db.count("Serial No")
		with self.assertRaisesRegex(frappe.ValidationError, "Missing-001.*does not exist"):
			SerialBatchBundleService(doc).create_serial_batch_bundle(details, doc.items[0])
		self.assertEqual(frappe.db.count("Serial No"), count)

	def test_the_item_entitles_serial_and_batch_work(self):
		user = self.make_role_user("identity-sales-user@example.com", "Sales User")
		serial = self.make_number("Serial No", "Existing-001")
		batch = self.make_number("Batch", "Existing-Batch")
		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Batch", "read"))
			self.assertFalse(frappe.has_permission("Batch", "create"))
			self.assertEqual(
				SerialBatchIdentity("Serial No").resolve(self.item.name, ["Existing-001"], create=True),
				[serial.name],
			)
			self.assertEqual(
				SerialBatchIdentity("Batch").resolve(self.item.name, ["Existing-Batch"]), [batch.name]
			)
			self.assertEqual(
				get_serial_batch_scan(self.item.name, "Existing-Batch", "Batch")["name"], batch.name
			)
			created = SerialBatchIdentity("Serial No").resolve(
				self.item.name, ["Missing-001"], create=True, defaults={"company": "_Test Company"}
			)
		self.assertEqual(
			frappe.db.get_value("Serial No", created[0], "serial_no"),
			"Missing-001",
		)

	def pos_profile(self):
		from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

		if not frappe.db.exists("POS Profile", "_Test POS Profile"):
			make_pos_profile()
		return "_Test POS Profile"

	def make_role_user(self, email, role):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Identity",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert()
		return email

	def make_receipt(self, serial_no):
		return frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"company": "_Test Company",
				"items": [{"item_code": self.item.name, "serial_no": serial_no}],
			}
		)

	def check_duplicate(self, doctype, number):
		first = self.make_number(doctype, "Number-001")
		duplicate = frappe.copy_doc(first)
		duplicate.set(SerialBatchIdentity(doctype).number_field, number)
		with self.assertRaisesRegex(frappe.UniqueValidationError, f"{number} already exists for Item"):
			duplicate.db_insert()

	def make_number(self, doctype, number, item_code=None):
		identity = SerialBatchIdentity(doctype)
		return frappe.get_doc(
			{
				"doctype": doctype,
				identity.item_field: item_code or self.item.name,
				identity.number_field: number,
				"company": "_Test Company",
			}
		).insert()
