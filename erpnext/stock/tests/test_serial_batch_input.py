import csv
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchInput(ERPNextTestSuite):
	def make_receipt(self, **properties):
		item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1, **properties})
		return make_purchase_receipt(item_code=item.name, qty=1, rate=100, do_not_save=True)

	def test_physical_input_is_created_on_save_and_used_on_submit(self):
		ids = []
		for _ in range(2):
			receipt = self.make_receipt()
			row = receipt.items[0]
			row.serial_number, row.batch_number = "Physical-Serial", "Physical-Batch"
			self.assertFalse(frappe.db.exists("Serial No", {"item_code": row.item_code}))
			receipt.insert()
			self.assertFalse(row.serial_number)
			self.assertFalse(row.batch_number)
			self.assertNotEqual(row.serial_no, "Physical-Serial")
			self.assertNotEqual(row.batch_no, "Physical-Batch")
			self.assertEqual(frappe.get_doc("Serial No", row.serial_no).status, "Inactive")
			ids.append(row.serial_no)
			receipt.submit()
			entry = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle).entries[0]
			self.assertEqual(entry.serial_no, ids[-1])
			self.assertEqual(frappe.get_doc("Serial No", ids[-1]).serial_no, "Physical-Serial")
			receipt.cancel()
		self.assertNotEqual(*ids)

	def test_failed_save_rolls_back_number_creation(self):
		receipt = self.make_receipt()
		row = receipt.items[0]
		row.serial_number, row.batch_number = "Rollback-Serial", "Rollback-Batch"
		frappe.db.savepoint("failed_physical_input")
		try:
			with patch.object(type(receipt), "validate", side_effect=frappe.ValidationError):
				with self.assertRaises(frappe.ValidationError):
					receipt.insert()
		finally:
			frappe.db.rollback(save_point="failed_physical_input")
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": row.item_code}))
		self.assertFalse(frappe.db.exists("Batch", {"item": row.item_code}))

	def test_auto_numbering_still_runs_on_submit(self):
		receipt = self.make_receipt(
			serial_no_series="AUTO-" + frappe.generate_hash() + "-.#####", create_new_batch=1
		)
		receipt.insert()
		item = receipt.items[0].item_code
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item}))
		receipt.submit()
		receipt.reload()
		bundle = frappe.get_doc("Serial and Batch Bundle", receipt.items[0].serial_and_batch_bundle)
		self.assertEqual(len(bundle.entries), 1)
		self.assertEqual(frappe.get_doc("Serial No", bundle.entries[0].serial_no).status, "Active")
		receipt.cancel()

	def test_series_collision_explains_how_to_fix_it(self):
		prefix = "COLLISION-" + frappe.generate_hash() + "-"
		receipt = self.make_receipt(has_batch_no=0, serial_no_series=prefix + ".#####")
		item = receipt.items[0].item_code
		SerialBatchIdentity("Serial No").resolve(item, [prefix + "00001"], create=True)
		receipt.insert()
		frappe.db.savepoint("series_collision")
		try:
			with self.assertRaises(frappe.DuplicateEntryError) as error:
				receipt.submit()
			self.assertIn("Serial No Series", str(error.exception))
			self.assertIn(item, str(error.exception))
		finally:
			frappe.db.rollback(save_point="series_collision")

	def test_existing_constraints_skip_data_scans(self):
		for doctype in ("Serial No", "Batch"):
			identity = SerialBatchIdentity(doctype)
			self.assertTrue(identity.has_constraint())
			with patch.object(identity, "validate_existing_numbers") as validate:
				with patch.object(identity, "backfill_numbers") as backfill:
					identity.sync_constraint()
			validate.assert_not_called()
			backfill.assert_not_called()

	def test_duplicate_physical_serials_are_rejected(self):
		receipt = self.make_receipt(has_batch_no=0)
		receipt.items[0].serial_number = "Same-Serial\nSAME-SERIAL"
		with self.assertRaises(frappe.ValidationError):
			receipt.insert()

	def test_internal_id_and_physical_input_cannot_conflict(self):
		receipt = self.make_receipt(has_batch_no=0)
		row = receipt.items[0]
		row.serial_no = SerialBatchIdentity("Serial No").resolve(row.item_code, ["One"], create=True)[0]
		row.serial_number = "Another"
		with self.assertRaises(frappe.ValidationError):
			receipt.insert()

	def test_bundle_save_resolves_physical_entries(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			add_serial_batch_ledgers,
		)

		receipt = self.make_receipt()
		receipt.insert()
		row = receipt.items[0]
		bundle = add_serial_batch_ledgers(
			entries=[{"serial_number": "Bundle-Serial", "batch_number": "Bundle-Batch", "qty": 1}],
			child_row=row.as_dict(),
			doc=receipt.as_dict(),
		)
		entry = bundle.entries[0]
		self.assertNotEqual(entry.serial_no, "Bundle-Serial")
		self.assertNotEqual(entry.batch_no, "Bundle-Batch")
		self.assertEqual(frappe.get_doc("Serial No", entry.serial_no).serial_no, "Bundle-Serial")
		self.assertEqual(frappe.get_doc("Batch", entry.batch_no).batch_id, "Bundle-Batch")

	def test_bundle_entry_preserves_an_explicit_batch(self):
		from erpnext.stock.serial_batch_identity import resolve_number_entries

		receipt = self.make_receipt()
		item = receipt.items[0].item_code
		batch, other_batch = SerialBatchIdentity("Batch").resolve(item, ["One", "Two"], create=True)
		serial = SerialBatchIdentity("Serial No").resolve(
			item, ["Bundled"], create=True, defaults={"batch_no": batch}
		)[0]
		entries = [{"serial_no": serial}, {"serial_no": serial, "batch_no": other_batch}]
		resolve_number_entries(item, entries)
		self.assertEqual(entries[0]["batch_no"], batch)
		self.assertEqual(entries[1]["batch_no"], other_batch)

	def test_data_import_accepts_explicit_physical_number_columns(self):
		from frappe.core.doctype.data_import.importer import ImportFile

		receipt = self.make_receipt()
		with NamedTemporaryFile(mode="w+", suffix=".csv") as file:
			writer = csv.writer(file)
			writer.writerow(
				[
					"supplier",
					"company",
					"items.item_code",
					"items.qty",
					"items.rate",
					"items.warehouse",
					"items.serial_number",
					"items.batch_number",
				]
			)
			writer.writerow(
				[
					receipt.supplier,
					receipt.company,
					receipt.items[0].item_code,
					1,
					100,
					receipt.items[0].warehouse,
					"Imported-Serial",
					"Imported-Batch",
				]
			)
			file.flush()
			payloads = ImportFile(
				"Purchase Receipt", file.name, import_type="Insert New Records", console=True
			).get_payloads_for_import()
		self.assertEqual(len(payloads), 1)
		imported = frappe.new_doc("Purchase Receipt").update(payloads[0].doc).insert()
		row = imported.items[0]
		self.assertEqual(frappe.get_doc("Serial No", row.serial_no).serial_no, "Imported-Serial")
		self.assertEqual(frappe.get_doc("Batch", row.batch_no).batch_id, "Imported-Batch")
