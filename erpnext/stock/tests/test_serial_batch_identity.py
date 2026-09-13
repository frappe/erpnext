from unittest.mock import patch

import frappe

from erpnext.controllers.sales_and_purchase_return import get_returned_serial_nos
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_reserved_serial_nos_for_pos,
	get_serial_batch_scan,
)
from erpnext.stock.doctype.serial_no.serial_no import auto_fetch_serial_number, get_pos_reserved_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_items, get_stock_balance_for
from erpnext.stock.report.stock_ledger.stock_ledger import update_available_serial_nos
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
			with self.assertRaisesRegex(frappe.ValidationError, "Missing-001.*_Identity Item A"):
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

	def test_scan_lookup_requires_read_permission(self):
		for doctype in ("Serial No", "Batch"):
			self.make_number(doctype, "Scan-001")
			with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
				get_serial_batch_scan(self.item.name, "Scan-001", doctype)

	def test_scan_lookup_works_without_serial_create_permission(self):
		serial = self.make_number("Serial No", "Scan-001")
		user = frappe.get_doc(
			doctype="User",
			email="identity-scan-reader@example.com",
			first_name="Scan Reader",
			send_welcome_email=0,
			roles=[{"role": "Stock User"}],
		).insert()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			self.assertEqual(
				get_serial_batch_scan(self.item.name, "Scan-001", "Serial No")["name"], serial.name
			)
			self.assertEqual(get_serial_batch_scan(self.item.name, "Missing-Scan", "Serial No"), {})
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "Missing-Scan"})
		)

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
			self.item.name, ["New-001", "existing-001", "NEW-001"], create=True
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

	def test_missing_serial_creation_requires_create_permission(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "identity-stock-user@example.com",
				"first_name": "Identity",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		).insert()
		serial = self.make_number("Serial No", "Existing-001")
		identity = SerialBatchIdentity("Serial No")
		with self.set_user(user.name):
			self.assertEqual(identity.resolve(self.item.name, ["Existing-001"], create=True), [serial.name])
			with self.assertRaises(frappe.PermissionError):
				identity.resolve(self.item.name, ["Missing-001"], create=True)
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "Missing-001"})
		)

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
