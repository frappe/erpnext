from unittest.mock import patch

import frappe
from frappe.core.doctype.data_import.importer import INSERT, UPDATE, ImportFile

from erpnext.stock.data_import import ERPNextDataImport, ERPNextExporter
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchDataImport(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Identity Import Item A", {"has_serial_no": 1, "has_batch_no": 1})
		self.other_item = make_item("_Identity Import Item B", {"has_serial_no": 1, "has_batch_no": 1})
		self.serial = self.make_number("Serial No", "Import-001")
		self.batch = self.make_number("Batch", "Import-001")
		self.other_serial = self.make_number("Serial No", "Import-001", self.other_item.name)
		self.other_batch = self.make_number("Batch", "Import-001", self.other_item.name)

	def test_transaction_import_resolves_batches_and_preserves_serial_text(self):
		rows = [
			["company", "items.item_code", "items.serial_no", "items.batch_no"],
			["_Test Company", self.item.name, "Import-001\nNew-002", "import-001"],
			["_Test Company", self.other_item.name, "Import-001", "Import-001"],
		]
		importer = self.make_importer("Purchase Receipt", rows)
		payloads = importer.import_file.get_payloads_for_import()
		self.assertEqual(payloads[0].doc["items"][0].batch_no, self.batch.name)
		self.assertEqual(payloads[1].doc["items"][0].batch_no, self.other_batch.name)
		self.assertEqual(payloads[0].doc["items"][0].serial_no, "Import-001\nNew-002")
		self.assertFalse(importer.import_file.get_all_warnings())
		self.assertEqual(importer.import_file.raw_data, rows)
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": self.item.name, "serial_no": "New-002"}))

	def test_bundle_import_uses_parent_item_and_separates_serial_and_batch_matches(self):
		rows = [
			["item_code", "entries.serial_no", "entries.batch_no", "entries.qty"],
			[self.item.name, "Import-001", "Import-001", 1],
			[self.other_item.name, "import-001", "import-001", 1],
		]
		importer = self.make_importer("Serial and Batch Bundle", rows)
		preview = importer.get_data_for_import_preview()
		self.assertEqual(preview.data[0][2:4], ["Import-001", "Import-001"])
		self.assertFalse(preview.warnings)
		payloads = importer.import_file.get_payloads_for_import()
		for payload, serial, batch in zip(
			payloads, [self.serial, self.other_serial], [self.batch, self.other_batch], strict=True
		):
			self.assertEqual(payload.doc.entries[0].serial_no, serial.name)
			self.assertEqual(payload.doc.entries[0].batch_no, batch.name)

	def test_invalid_numbers_warn_without_creating_records(self):
		before = {doctype: frappe.db.count(doctype) for doctype in ("Serial No", "Batch")}
		importer = self.make_importer(
			"Serial and Batch Bundle",
			[
				["item_code", "entries.serial_no", "entries.batch_no"],
				[self.item.name, "Missing-Serial", "Missing-Batch"],
			],
		)
		preview = importer.get_data_for_import_preview()
		self.assertEqual(len(preview.warnings), 2)
		self.assertTrue(all(warning["row"] == 2 for warning in preview.warnings))
		self.assertIn("Missing-Serial", preview.warnings[0]["message"])
		self.assertIn("Missing-Batch", preview.warnings[1]["message"])
		for doctype, count in before.items():
			self.assertEqual(frappe.db.count(doctype), count)

	def test_link_values_are_always_physical_numbers(self):
		serial = self.make_number("Serial No", self.serial.name)
		importer = self.make_importer(
			"Maintenance Visit",
			[
				["customer", "purposes.item_code", "purposes.serial_no"],
				["_Test Customer", self.item.name, self.serial.name],
			],
		)
		payload = importer.import_file.get_payloads_for_import()[0]
		self.assertEqual(payload.doc.purposes[0].serial_no, serial.name)

	def test_bundle_export_round_trip_preserves_stored_ids(self):
		bundle = frappe.get_doc(doctype="Serial and Batch Bundle", item_code=self.item.name)
		bundle.db_insert()
		entry = bundle.append(
			"entries", {"serial_no": self.serial.name, "batch_no": self.batch.name, "qty": 1}
		)
		entry.db_insert()
		exporter = ERPNextExporter(
			bundle.doctype,
			export_fields={bundle.doctype: ["name"], "entries": ["name", "serial_no", "batch_no", "qty"]},
			export_data=True,
			export_filters={"name": bundle.name},
		)
		rows = exporter.get_csv_array()
		self.assertIn("Item Code", rows[0])
		self.assertEqual(rows[1].count("Import-001"), 2)
		self.assertNotIn(self.serial.name, rows[1])
		self.assertNotIn(self.batch.name, rows[1])
		importer = self.make_importer(bundle.doctype, rows, UPDATE)
		payload = importer.import_file.get_payloads_for_import()[0]
		self.assertEqual(payload.doc.entries[0].serial_no, self.serial.name)
		self.assertEqual(payload.doc.entries[0].batch_no, self.batch.name)
		stored = frappe.get_doc("Serial and Batch Entry", entry.name)
		self.assertEqual(stored.serial_no, self.serial.name)
		self.assertEqual(stored.batch_no, self.batch.name)

	def test_serial_master_import_keeps_the_physical_data_field(self):
		importer = self.make_importer(
			"Serial No", [["item_code", "serial_no"], [self.item.name, "New-Serial"]]
		)
		self.assertEqual(importer.import_file.get_payloads_for_import()[0].doc.serial_no, "New-Serial")
		self.assertFalse(importer.import_file.get_all_warnings())

	def test_serial_and_batch_lookup_respects_permissions(self):
		importer = self.make_importer(
			"Serial and Batch Bundle",
			[
				["item_code", "entries.serial_no", "entries.batch_no"],
				[self.item.name, "Import-001", "Import-001"],
			],
		)
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			importer.get_data_for_import_preview()

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

	def make_importer(self, doctype, rows, import_type=INSERT):
		file = frappe.get_doc(
			doctype="File",
			file_name="identity-import.csv",
			file_url=f"/private/files/{frappe.generate_hash()}.csv",
			is_private=1,
		)
		file.db_insert()
		data_import = frappe.new_doc("Data Import")
		self.assertIsInstance(data_import, ERPNextDataImport)
		data_import.update(
			{"reference_doctype": doctype, "import_type": import_type, "import_file": file.file_url}
		)
		with patch.object(ImportFile, "get_data_from_template_file", return_value=rows):
			return data_import.get_importer()
