from unittest.mock import patch

import frappe

from erpnext.stock.doctype.item.test_item import make_item
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
