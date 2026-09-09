import csv
from pathlib import Path
from tempfile import TemporaryDirectory
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
			row.serial_no, row.batch_no = "Physical-Serial", "Physical-Batch"
			row.set("__serial_batch_input", ["serial_no", "batch_no"])
			self.assertFalse(frappe.db.exists("Serial No", {"item_code": row.item_code}))
			receipt.insert()
			self.assertFalse(row.get("__serial_batch_input"))
			self.assertNotIn("__serial_batch_input", receipt.as_dict()["items"][0])
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
		row.serial_no, row.batch_no = "Rollback-Serial", "Rollback-Batch"
		row.set("__serial_batch_input", ["serial_no", "batch_no"])
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
		receipt.items[0].serial_no = "Same-Serial\nSAME-SERIAL"
		receipt.items[0].set("__serial_batch_input", ["serial_no"])
		with self.assertRaises(frappe.ValidationError):
			receipt.insert()

	def test_physical_input_never_falls_back_to_an_internal_id(self):
		receipt = self.make_receipt(has_batch_no=0)
		row = receipt.items[0]
		identity = SerialBatchIdentity("Serial No")
		original = identity.resolve(row.item_code, ["One"], create=True)[0]
		other = identity.resolve(row.item_code, [original], create=True)[0]
		row.serial_no = original
		row.set("__serial_batch_input", ["serial_no"])
		receipt.insert()
		self.assertEqual(row.serial_no, other)
		receipt.save()
		self.assertEqual(row.serial_no, other)
		receipt.reload()
		self.assertEqual(row.serial_no, other)

	def test_unmarked_fields_preserve_internal_ids(self):
		receipt = self.make_receipt()
		row = receipt.items[0]
		row.serial_no = SerialBatchIdentity("Serial No").resolve(row.item_code, ["One"], create=True)[0]
		row.batch_no = SerialBatchIdentity("Batch").resolve(row.item_code, ["One"], create=True)[0]
		ids = row.serial_no, row.batch_no
		receipt.insert()
		self.assertEqual((row.serial_no, row.batch_no), ids)

	def test_request_metadata_survives_serialization_until_save(self):
		receipt = self.make_receipt()
		row = receipt.items[0]
		row.serial_no, row.batch_no = "API-Serial", "API-Batch"
		row.set("__serial_batch_input", ["serial_no", "batch_no"])
		payload = frappe.parse_json(receipt.as_json())
		self.assertEqual(payload["items"][0]["__serial_batch_input"], ["serial_no", "batch_no"])
		saved = frappe.get_doc(payload).insert()
		self.assertEqual(frappe.get_doc("Serial No", saved.items[0].serial_no).serial_no, "API-Serial")
		self.assertEqual(frappe.get_doc("Batch", saved.items[0].batch_no).batch_id, "API-Batch")
		self.assertNotIn("__serial_batch_input", saved.as_dict()["items"][0])

	def test_input_metadata_cannot_target_other_fields(self):
		receipt = self.make_receipt()
		receipt.items[0].set("__serial_batch_input", ["item_code"])
		with self.assertRaises(frappe.ValidationError):
			receipt.insert()

	def test_no_extra_transaction_number_fields(self):
		for doctype in frappe.get_all(
			"DocField", filters={"fieldname": "serial_and_batch_bundle"}, pluck="parent", distinct=True
		):
			meta = frappe.get_meta(doctype)
			for field in ("serial_number", "batch_number", "rejected_serial_number", "current_serial_number"):
				self.assertFalse(meta.has_field(field), (doctype, field))

	def test_input_requires_a_bundle_field(self):
		from erpnext.stock.serial_batch_input import resolve_transaction_numbers

		receipt = self.make_receipt()
		row = receipt.items[0]
		row.serial_no = "Pending-Serial"
		row.set("__serial_batch_input", ["serial_no"])
		with patch.object(row.meta, "has_field", return_value=False):
			resolve_transaction_numbers(receipt)
		self.assertEqual(row.serial_no, "Pending-Serial")
		self.assertNotIn("__serial_batch_input", receipt.as_dict(no_private_properties=True)["items"][0])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": row.item_code}))

	def test_number_inputs_follow_child_field_metadata(self):
		from erpnext.stock.serial_batch_import import has_number_inputs
		from erpnext.stock.serial_batch_input import resolve_transaction_numbers

		doctype = "Installation Note Item"
		meta = frappe.get_meta(doctype)
		with patch.dict(
			meta._fields,
			{field: df for field, df in meta._fields.items() if field != "serial_and_batch_bundle"},
			clear=True,
		):
			self.assertFalse(has_number_inputs("Installation Note"))
			meta._fields["serial_and_batch_bundle"] = frappe._dict(
				fieldname="serial_and_batch_bundle", fieldtype="Data"
			)
			self.assertTrue(has_number_inputs("Installation Note"))
			receipt = self.make_receipt(has_batch_no=0)
			item = receipt.items[0].item_code
			serial = SerialBatchIdentity("Serial No").resolve(item, ["Custom-Serial"], create=True)[0]
			doc = frappe.get_doc(doctype="Installation Note", items=[{"item_code": item}])
			row = doc.items[0]
			row.serial_no = "Custom-Serial"
			row.set("__serial_batch_input", ["serial_no"])
			payload = frappe.parse_json(doc.as_json())
			self.assertEqual(payload["items"][0]["__serial_batch_input"], ["serial_no"])
			resolve_transaction_numbers(doc)
			self.assertEqual(row.serial_no, serial)

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

	def test_data_import_can_explicitly_preserve_internal_ids(self):
		from erpnext.stock.serial_batch_import import SerialBatchImporter

		receipt = self.make_receipt()
		item = receipt.items[0].item_code
		serial = SerialBatchIdentity("Serial No").resolve(item, ["Exported-Serial"], create=True)[0]
		batch = SerialBatchIdentity("Batch").resolve(item, ["Exported-Batch"], create=True)[0]
		with TemporaryDirectory() as directory:
			path = Path(directory) / "internal_ids.csv"
			with path.open("w", newline="") as file:
				writer = csv.writer(file)
				writer.writerow(
					["supplier", "company", "items.item_code", "items.serial_no", "items.batch_no"]
				)
				writer.writerow([receipt.supplier, receipt.company, item, serial, batch])
			importer = SerialBatchImporter(
				"Purchase Receipt",
				file_path=str(path),
				console=True,
				data_import=frappe.get_doc(
					doctype="Data Import",
					import_type="Insert New Records",
					template_options=frappe.as_json({"column_to_field_map": {}, "serial_batch_input": False}),
				),
			)
			row = importer.import_file.get_payloads_for_import()[0].doc["items"][0]
			self.assertFalse(row.get("__serial_batch_input"))
			self.assertEqual((row.serial_no, row.batch_no), (serial, batch))

	def test_data_import_reuses_existing_number_columns(self):
		from erpnext.stock.serial_batch_import import SerialBatchImporter

		receipt = self.make_receipt()
		with TemporaryDirectory() as directory:
			path = Path(directory) / "physical_numbers.csv"
			with path.open("w", newline="") as file:
				writer = csv.writer(file)
				writer.writerow(
					[
						"supplier",
						"company",
						"items.item_code",
						"items.qty",
						"items.rate",
						"items.warehouse",
						"items.serial_no",
						"items.batch_no",
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
			importer = SerialBatchImporter(
				"Purchase Receipt",
				file_path=str(path),
				import_type="Insert New Records",
				console=True,
				data_import=frappe.get_doc(doctype="Data Import", import_type="Insert New Records"),
			)
			payloads = importer.import_file.get_payloads_for_import()
			self.assertFalse(importer.import_file.get_all_warnings())
			file = frappe.get_doc(
				doctype="File", file_name="physical_numbers.csv", content=path.read_text(), is_private=1
			).insert()
			self.addCleanup(frappe.delete_doc, "File", file.name)
		self.assertEqual(len(payloads), 1)
		data_import = frappe.get_doc(
			doctype="Data Import",
			reference_doctype="Purchase Receipt",
			import_type="Insert New Records",
			import_file=file.file_url,
			submit_after_import=1,
		).insert()
		self.assertIsInstance(data_import.get_importer(), SerialBatchImporter)
		with patch.object(frappe.db, "commit"):
			data_import.start_import()
		self.assertEqual(data_import.reload().status, "Success")
		imported = frappe.get_doc(
			"Purchase Receipt",
			frappe.db.get_value("Data Import Log", {"data_import": data_import.name}, "docname"),
		)
		self.assertEqual(imported.docstatus, 1)
		row = imported.items[0]
		entry = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle).entries[0]
		self.assertEqual(frappe.get_doc("Serial No", entry.serial_no).serial_no, "Imported-Serial")
		self.assertEqual(frappe.get_doc("Batch", entry.batch_no).batch_id, "Imported-Batch")
		imported.cancel()
