from unittest.mock import patch

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
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
