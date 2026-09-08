from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.serial_batch_identity import SerialBatchIdentity, resolve_number_entries
from erpnext.stock.serial_batch_input import TransactionNumberInput
from erpnext.stock.serial_batch_number_lookup import SerialBatchNumberLookup
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchNumberLookup(ERPNextTestSuite):
	def make_item_and_identity(self, doctype):
		item = make_item(properties={"has_serial_no": 1, "has_batch_no": int(doctype == "Batch")})
		identity = SerialBatchIdentity(doctype)
		identity.resolve(item.name, ["Existing"], create=True)
		return item, identity

	def test_existing_number_aliases_use_one_query(self):
		for doctype in ("Serial No", "Batch"):
			item, identity = self.make_item_and_identity(doctype)
			numbers = [f"Number-{index:03d}" for index in range(50)]
			ids = identity.resolve(item.name, numbers, create=True)
			requested = [number.swapcase() for number in reversed(numbers)] + [numbers[0].upper()]
			with self.assert_select_query_count(1):
				resolved = identity.resolve(item.name, requested, create=True)
			self.assertEqual(resolved, [*reversed(ids), ids[0]])

	def test_new_serial_aliases_share_one_lookup_and_bulk_insert(self):
		item, identity = self.make_item_and_identity("Serial No")
		numbers = [f"New-{index:03d}" for index in range(100)]
		with patch.object(frappe.db, "bulk_insert", wraps=frappe.db.bulk_insert) as insert:
			with self.assert_select_query_count(1):
				ids = identity.resolve(
					item.name, numbers + [number.upper() for number in numbers], create=True
				)
		insert.assert_called_once()
		self.assertEqual(ids[:100], ids[100:])
		self.assertEqual(len(set(ids)), 100)
		self.assertEqual(identity.labels([ids[0]]), {ids[0]: numbers[0]})

	def test_duplicate_retry_remains_batched(self):
		item, identity = self.make_item_and_identity("Serial No")
		numbers = [f"Retry-{index:03d}" for index in range(50)]
		create_many = identity.create_many
		attempts = []

		def create(item_code, requested, defaults):
			attempts.append(requested)
			if len(attempts) == 1:
				raise frappe.DuplicateEntryError
			return create_many(item_code, requested, defaults)

		with patch.object(identity, "create_many", side_effect=create):
			with self.assert_select_query_count(2):
				ids = identity.resolve(
					item.name, numbers + [number.upper() for number in numbers], create=True
				)
		self.assertEqual(attempts, [numbers, numbers])
		self.assertEqual(ids[:50], ids[50:])

	def test_batch_creation_keeps_lifecycle_validation(self):
		item = make_item(properties={"has_batch_no": 1, "has_expiry_date": 1, "shelf_life_in_days": 30})
		identity = SerialBatchIdentity("Batch")
		with patch.object(SerialBatchIdentity, "exists", side_effect=AssertionError("Per-number lookup")):
			names = identity.resolve(
				item.name,
				["Batch-One", "BATCH-ONE", "Batch-Two"],
				create=True,
				defaults={"manufacturing_date": today()},
			)
		self.assertEqual(names[0], names[1])
		self.assertNotEqual(names[0], names[2])
		batch = frappe.get_doc("Batch", names[0])
		self.assertEqual(getdate(batch.expiry_date), getdate(add_days(today(), 30)))
		self.assertEqual(batch.use_batchwise_valuation, 1)

	def test_prechecked_batch_still_has_database_uniqueness(self):
		item, identity = self.make_item_and_identity("Batch")
		frappe.db.savepoint("prechecked_batch")
		try:
			with self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError)):
				identity.create_batch(item.name, "EXISTING")
		finally:
			frappe.db.rollback(save_point="prechecked_batch")

	def test_transaction_and_bundle_resolution_reuse_the_lookup(self):
		item, identity = self.make_item_and_identity("Serial No")
		numbers = [f"Selected-{index:03d}" for index in range(50)]
		names = identity.resolve(item.name, numbers, create=True)
		receipt = make_purchase_receipt(item_code=item.name, qty=50, do_not_save=True)
		row = receipt.items[0]
		row.serial_number = "\n".join(number.lower() for number in numbers)
		load = SerialBatchNumberLookup.load
		with patch.object(SerialBatchNumberLookup, "load", autospec=True, side_effect=load) as lookup:
			TransactionNumberInput(receipt, row).resolve()
			lookup.assert_called_once()
		self.assertEqual(row.serial_no.splitlines(), names)
		entries = [{"serial_number": number.lower()} for number in numbers]
		with patch.object(SerialBatchNumberLookup, "load", autospec=True, side_effect=load) as lookup:
			resolve_number_entries(item.name, entries, create=True)
			lookup.assert_called_once()
		self.assertEqual([entry["serial_no"] for entry in entries], names)

	def test_bound_numbers_do_not_become_sql(self):
		item, identity = self.make_item_and_identity("Serial No")
		numbers = ["Serial'One", "100%_Matched", 'A"B']
		names = identity.resolve(item.name, numbers, create=True)
		self.assertEqual(identity.resolve(item.name, numbers), names)
		self.assertEqual(identity.labels(names), dict(zip(names, numbers, strict=True)))

	@contextmanager
	def assert_select_query_count(self, count):
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			yield
		queries = [str(call.args[0]) for call in sql.call_args_list]
		selects = [query for query in queries if query.lstrip().lower().startswith("select")]
		self.assertEqual(len(selects), count, "\n".join(selects))
