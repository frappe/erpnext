# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

import frappe
from frappe.utils import add_days, getdate

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import (
	append_scanned_batches,
	download_bundle_entries_csv,
	get_bundle_entries,
	resolve_csv_entries,
	upsert_bundle_entries,
)
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	add_serial_batch_ledgers,
	read_serial_batch_csv,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchInlineEditor(ERPNextTestSuite):
	def make_draft_pr(self, item_code, qty=2):
		return make_purchase_receipt(item_code=item_code, qty=qty, rate=100, do_not_submit=True)

	def upsert(
		self,
		pr,
		entries=None,
		deleted=None,
		is_rejected=0,
		replace=0,
		serial_numbers=None,
		batch_numbers=None,
		csv_entries=None,
	):
		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = is_rejected

		return upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			entries=json.dumps(entries or []),
			deleted=json.dumps(deleted or []),
			replace=replace,
			serial_numbers=json.dumps(serial_numbers or []),
			batch_numbers=json.dumps(batch_numbers or []),
			csv_entries=json.dumps(csv_entries or []),
		)

	def reload_row(self, pr):
		pr.reload()
		return pr.items[0]

	def save_selector(self, pr, entries=None, csv_entries=None):
		return add_serial_batch_ledgers(
			entries=json.dumps(entries or []),
			child_row=json.dumps(pr.items[0].as_dict(), default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			csv_entries=json.dumps(csv_entries or []),
		)

	def test_create_bundle_with_serials(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [self.make_serial(item) for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		self.assertTrue(frappe.db.exists("Serial and Batch Bundle", summary.bundle))
		self.assertEqual(summary.total_count, 2)
		self.assertEqual(summary.total_qty, 2)
		for serial_no in serials:
			self.assertTrue(frappe.db.exists("Serial No", serial_no))

	def test_scanned_serials_resolve_by_item_on_save(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		other_item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		other_serial = self.make_serial(other_item, "Scan-001")
		pr = self.make_draft_pr(item, qty=1)
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Scan-001"}))

		summary = self.upsert(pr, serial_numbers=["Scan-001", "scan-001"])
		self.assertEqual(summary.total_count, 1)
		self.assertEqual(summary.total_qty, 1)
		serial_id = frappe.db.get_value("Serial and Batch Entry", {"parent": summary.bundle}, "serial_no")
		serial = frappe.get_doc("Serial No", serial_id)
		self.assertEqual(serial.item_code, item)
		self.assertEqual(serial.serial_no, "Scan-001")
		self.assertEqual(serial.company, pr.company)
		self.assertNotIn(serial_id, ["Scan-001", other_serial])

	def test_rescan_after_reselection_keeps_one_entry(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, serial_numbers=["Scan-001"])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		entry_name = frappe.db.get_value("Serial and Batch Entry", {"parent": summary.bundle})
		replacement = self.make_serial(item, "Scan-002")

		summary = self.upsert(
			pr,
			entries=[{"name": entry_name, "serial_no": replacement}],
			serial_numbers=["scan-002"],
		)
		self.assertEqual(summary.total_count, 1)
		self.assertEqual(summary.total_qty, 1)
		self.assertEqual(frappe.db.get_value("Serial and Batch Entry", entry_name, "serial_no"), replacement)

	def test_outward_scan_does_not_create_a_serial(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		pr.is_return = 1
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			self.upsert(pr, serial_numbers=["Missing-Scan"])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Scan"}))

	def test_scanned_serial_is_created_for_a_user_who_may_write_the_voucher(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "inline-scan-stock-user@example.com",
				"first_name": "Inline Scan",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		).insert()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			self.upsert(pr, serial_numbers=["Missing-Scan"])
		self.assertTrue(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Scan"}))

	def test_scan_cannot_override_outward_transaction_type(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		doc = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": "_Test Company",
				"items": [{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 1}],
			}
		)
		doc.items[0].type_of_transaction = "Inward"
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			self.upsert(doc, serial_numbers=["Missing-Scan"])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Scan"}))

	def test_incremental_append_preserves_existing_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		serials = [self.make_serial(item) for _ in range(3)]

		summary = self.upsert(pr, entries=[{"serial_no": serials[0]}, {"serial_no": serials[1]}])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		first_entry_names = set(
			frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")
		)

		summary = self.upsert(pr, entries=[{"serial_no": serials[2]}])
		second_entry_names = set(
			frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")
		)

		self.assertEqual(summary.total_count, 3)
		self.assertTrue(first_entry_names.issubset(second_entry_names))

	def test_delete_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [self.make_serial(item) for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])
		pr.items[0].serial_and_batch_bundle = summary.bundle

		to_delete = frappe.get_all(
			"Serial and Batch Entry", {"parent": summary.bundle, "serial_no": serials[0]}, pluck="name"
		)
		summary = self.upsert(pr, deleted=to_delete)

		self.assertEqual(summary.total_count, 1)
		remaining = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="serial_no")
		self.assertEqual(remaining, [serials[1]])

	def test_batch_scans_resolve_by_item_and_keep_expiry(self):
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "has_expiry_date": 1, "shelf_life_in_days": 30}
		).name
		other = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		other_batch = frappe.get_doc({"doctype": "Batch", "item": other, "batch_id": "Scan-Batch"}).insert()
		pr = self.make_draft_pr(item, qty=3)
		summary = self.upsert(
			pr,
			batch_numbers=[
				{"batch_number": "Scan-Batch", "qty": 1},
				{"batch_number": "scan-batch", "qty": 2},
			],
		)
		self.assertEqual(summary.total_count, 1)
		self.assertEqual(summary.total_qty, 3)
		batch_id = frappe.db.get_value("Serial and Batch Entry", {"parent": summary.bundle}, "batch_no")
		batch = frappe.get_doc("Batch", batch_id)
		self.assertEqual(batch.item, item)
		self.assertEqual(batch.batch_id, "Scan-Batch")
		self.assertNotIn(batch.name, [batch.batch_id, other_batch.name])
		self.assertEqual(getdate(batch.expiry_date), getdate(add_days(batch.manufacturing_date, 30)))

	def test_batch_rescan_adds_to_reselected_entry(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, batch_numbers=[{"batch_number": "Scan-Old", "qty": 1}])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		entry_name = frappe.db.get_value("Serial and Batch Entry", {"parent": summary.bundle})
		replacement = frappe.get_doc({"doctype": "Batch", "item": item, "batch_id": "Scan-New"}).insert()
		summary = self.upsert(
			pr,
			entries=[{"name": entry_name, "batch_no": replacement.name, "qty": 4}],
			batch_numbers=[{"batch_number": "scan-new", "qty": 2}],
		)
		self.assertEqual(summary.total_count, 1)
		self.assertEqual(summary.total_qty, 6)
		self.assertEqual(
			frappe.db.get_value("Serial and Batch Entry", entry_name, "batch_no"), replacement.name
		)

	def test_outward_batch_scan_does_not_create_a_batch(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		pr.is_return = 1
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			self.upsert(pr, batch_numbers=[{"batch_number": "Missing-Batch", "qty": 1}])
		self.assertFalse(frappe.db.exists("Batch", {"item": item, "batch_id": "Missing-Batch"}))

	def test_batch_scan_requires_positive_quantity(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		for qty in (0, -1):
			with self.assertRaisesRegex(frappe.ValidationError, "greater than zero"):
				self.upsert(pr, batch_numbers=[{"batch_number": "Missing-Batch", "qty": qty}])
		self.assertFalse(frappe.db.exists("Batch", {"item": item, "batch_id": "Missing-Batch"}))

	def test_batch_rescan_preserves_outward_quantity_sign(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc({"doctype": "Batch", "item": item, "batch_id": "Scan-Batch"}).insert()
		entry = frappe._dict(batch_no=batch.name, qty=-4)
		new_entries = append_scanned_batches(
			[], [{"batch_number": "Scan-Batch", "qty": 2}], item, "Outward", [entry]
		)
		self.assertEqual(new_entries, [])
		self.assertEqual(entry.qty, -6)

	def test_batch_qty_update(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TSTBIE-.####",
			}
		).name
		pr = self.make_draft_pr(item, qty=5)
		batch = frappe.get_doc(doctype="Batch", item=item).insert()

		summary = self.upsert(pr, entries=[{"batch_no": batch.name, "qty": 5}])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		self.assertEqual(summary.total_qty, 5)

		entry_name = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")[0]
		summary = self.upsert(pr, entries=[{"name": entry_name, "qty": 8}])

		self.assertEqual(summary.total_qty, 8)
		self.assertEqual(summary.total_count, 1)

	def test_update_serial_no_of_existing_entry(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		old_serial = self.make_serial(item)
		new_serial = self.make_serial(item)

		summary = self.upsert(pr, entries=[{"serial_no": old_serial}])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		entry_name = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")[0]

		self.upsert(pr, entries=[{"name": entry_name, "serial_no": new_serial}])

		self.assertEqual(frappe.db.get_value("Serial and Batch Entry", entry_name, "serial_no"), new_serial)
		self.assertTrue(frappe.db.exists("Serial No", new_serial))

	def test_link_values_do_not_create_missing_records(self):
		for doctype, field, item_field, number_field, item_properties in (
			("Serial No", "serial_no", "item_code", "serial_no", {"has_serial_no": 1}),
			("Batch", "batch_no", "item", "batch_id", {"has_batch_no": 1}),
		):
			item = make_item(properties={"is_stock_item": 1, **item_properties}).name
			pr = self.make_draft_pr(item, qty=1)
			number = f"Missing-{frappe.generate_hash(length=8)}"
			with self.assertRaises(frappe.LinkValidationError):
				self.upsert(pr, entries=[{field: number, "qty": 1}])
			self.assertFalse(frappe.db.exists(doctype, {item_field: item, number_field: number}))

			master = frappe.get_doc(
				{"doctype": doctype, item_field: item, number_field: number, "company": pr.company}
			).insert()
			with self.assertRaises(frappe.LinkValidationError):
				self.upsert(pr, entries=[{field: number, "qty": 1}])
			summary = self.upsert(pr, entries=[{field: master.name, "qty": 1}])
			pr.items[0].serial_and_batch_bundle = summary.bundle
			entry_name = frappe.db.get_value("Serial and Batch Entry", {"parent": summary.bundle})
			with self.assertRaises(frappe.LinkValidationError):
				self.upsert(pr, entries=[{"name": entry_name, field: number}])
			self.assertEqual(frappe.db.get_value("Serial and Batch Entry", entry_name, field), master.name)

	def test_update_batch_no_of_existing_entry(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TSTBIE-.####",
			}
		).name
		pr = self.make_draft_pr(item, qty=5)
		batch1 = frappe.get_doc(doctype="Batch", item=item).insert()
		batch2 = frappe.get_doc(doctype="Batch", item=item).insert()

		summary = self.upsert(pr, entries=[{"batch_no": batch1.name, "qty": 5}])
		pr.items[0].serial_and_batch_bundle = summary.bundle

		entry_name = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")[0]
		self.upsert(pr, entries=[{"name": entry_name, "batch_no": batch2.name}])

		entry = frappe.db.get_value("Serial and Batch Entry", entry_name, ["batch_no", "qty"], as_dict=1)
		self.assertEqual(entry.batch_no, batch2.name)
		self.assertEqual(entry.qty, 5)

	def test_delete_all_entries_removes_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [self.make_serial(item) for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])
		bundle = summary.bundle
		pr.items[0].serial_and_batch_bundle = bundle
		pr.items[0].db_set("serial_and_batch_bundle", bundle)

		to_delete = frappe.get_all("Serial and Batch Entry", {"parent": bundle}, pluck="name")
		summary = self.upsert(pr, deleted=to_delete)

		self.assertFalse(summary.bundle)
		self.assertEqual(summary.total_count, 0)
		self.assertFalse(frappe.db.exists("Serial and Batch Bundle", bundle))
		self.assertFalse(
			frappe.db.get_value("Purchase Receipt Item", pr.items[0].name, "serial_and_batch_bundle")
		)

	def test_remove_empty_bundle_ignores_spoofed_child_row(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		victim_pr = self.make_draft_pr(item)

		summary = self.upsert(pr, entries=[{"serial_no": self.make_serial(item)}])
		bundle = summary.bundle
		pr.items[0].db_set("serial_and_batch_bundle", bundle)

		victim_summary = self.upsert(victim_pr, entries=[{"serial_no": self.make_serial(item)}])
		victim_bundle = victim_summary.bundle
		victim_pr.items[0].db_set("serial_and_batch_bundle", victim_bundle)

		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = 0
		child_row["name"] = victim_pr.items[0].name

		to_delete = frappe.get_all("Serial and Batch Entry", {"parent": bundle}, pluck="name")
		upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			deleted=json.dumps(to_delete),
		)

		self.assertFalse(frappe.db.exists("Serial and Batch Bundle", bundle))
		self.assertEqual(
			frappe.db.get_value("Purchase Receipt Item", victim_pr.items[0].name, "serial_and_batch_bundle"),
			victim_bundle,
		)

	def test_csv_read_preserves_numbers_without_creating_records(self):
		cases = [
			("Serial No\nCSV-Serial", ([{"serial_no": "CSV-Serial", "qty": 1}], [])),
			("Batch No,Qty\nCSV-Batch,2", ([], [{"batch_no": "CSV-Batch", "qty": "2"}])),
			(
				"Serial No,Batch No,Qty\nCSV-Serial,CSV-Batch,1",
				(
					[{"serial_no": "CSV-Serial", "batch_no": "CSV-Batch", "qty": "1"}],
					[{"batch_no": "CSV-Batch", "qty": "1"}],
				),
			),
		]
		for content, expected in cases:
			with self.subTest(content=content):
				file = Mock(file_type="CSV")
				file.get_content.return_value = content
				with patch(
					"frappe.core.doctype.file.utils.find_file_by_url", return_value=file
				) as find_file, patch("frappe.db.bulk_insert") as insert:
					self.assertEqual(read_serial_batch_csv("/private/files/serials.csv"), expected)
					find_file.assert_called_once_with("/private/files/serials.csv")
					insert.assert_not_called()
				file.check_permission.assert_called_once_with("read")
				file.insert.assert_not_called()

	def test_csv_read_requires_file_permission(self):
		file = Mock(file_type="CSV")
		file.check_permission.side_effect = frappe.PermissionError
		with patch("frappe.core.doctype.file.utils.find_file_by_url", return_value=file), self.assertRaises(
			frappe.PermissionError
		):
			read_serial_batch_csv("/private/files/serials.csv")
		file.get_content.assert_not_called()

	def test_csv_rows_resolve_serial_batch_pairs(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": 1}).name
		other = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(doctype="Batch", item=other, batch_id="CSV-Batch").insert()
		frappe.get_doc(
			doctype="Serial No",
			item_code=other,
			serial_no="CSV-Serial",
			batch_no=batch.name,
			company="_Test Company",
		).insert()
		rows = [{"serial_no": "CSV-Serial", "batch_no": "CSV-Batch", "qty": 1}]
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, csv_entries=rows)
		entry = frappe.get_doc("Serial and Batch Bundle", summary.bundle).entries[0]
		serial = frappe.get_doc("Serial No", entry.serial_no)
		batch = frappe.get_doc("Batch", entry.batch_no)
		self.assertEqual((serial.item_code, serial.serial_no), (item, "CSV-Serial"))
		self.assertEqual((batch.item, batch.batch_id), (item, "CSV-Batch"))
		self.assertEqual(serial.batch_no, batch.name)
		self.assertEqual(serial.company, pr.company)
		self.assertEqual(rows, [{"serial_no": "CSV-Serial", "batch_no": "CSV-Batch", "qty": 1}])

	def test_csv_resolution_keeps_the_source_rows_unchanged(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		rows = [{"serial_no": "CSV-Serial", "qty": 1}]
		resolved = resolve_csv_entries(rows, item, "Inward", "_Test Company")
		self.assertNotEqual(resolved[0].serial_no, rows[0]["serial_no"])
		self.assertEqual(rows, [{"serial_no": "CSV-Serial", "qty": 1}])

	def test_csv_reselection_preserves_link_ids(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(doctype="Batch", item=item, batch_id="Selected-Batch").insert()
		serial = frappe.get_doc(
			doctype="Serial No",
			item_code=item,
			serial_no="Selected-Serial",
			batch_no=batch.name,
			company="_Test Company",
		).insert()
		rows = [
			{"serial_no_id": serial.name, "batch_no": batch.batch_id, "qty": 1},
			{"serial_no": serial.serial_no, "batch_no_id": batch.name, "qty": 1},
			{"serial_no_id": serial.name, "batch_no_id": batch.name, "qty": 1},
		]
		for row in rows:
			with self.subTest(row=row):
				resolved = resolve_csv_entries([row], item, "Outward", "_Test Company")
				self.assertEqual(resolved, [{"serial_no": serial.name, "batch_no": batch.name, "qty": 1}])

	def test_csv_new_serial_uses_reselected_batch(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(doctype="Batch", item=item, batch_id="Selected-Batch").insert()
		rows = [{"serial_no": "CSV-Serial", "batch_no_id": batch.name, "qty": 1}]
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, csv_entries=rows)
		entry = frappe.get_doc("Serial and Batch Bundle", summary.bundle).entries[0]
		serial = frappe.get_doc("Serial No", entry.serial_no)
		self.assertEqual(serial.serial_no, "CSV-Serial")
		self.assertEqual(serial.batch_no, batch.name)
		self.assertEqual(entry.batch_no, batch.name)
		self.assertFalse(frappe.db.exists("Batch", {"item": item, "batch_id": batch.name}))

	def test_csv_replace_uses_reselected_serial(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, serial_numbers=["Original-Serial"])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		selected = self.make_serial(item, "Selected-Serial")
		summary = self.upsert(pr, csv_entries=[{"serial_no_id": selected, "qty": 1}], replace=1)
		bundle = frappe.get_doc("Serial and Batch Bundle", summary.bundle)
		self.assertEqual([entry.serial_no for entry in bundle.entries], [selected])
		self.assertEqual(summary.total_qty, 1)
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": selected}))

	def test_outward_csv_does_not_create_missing_records(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": 1}).name
		rows = [{"serial_no": "CSV-Serial", "batch_no": "CSV-Batch", "qty": 1}]
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			resolve_csv_entries(rows, item, "Outward", "_Test Company")
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "CSV-Serial"}))
		self.assertFalse(frappe.db.exists("Batch", {"item": item, "batch_id": "CSV-Batch"}))

	def test_csv_export_uses_physical_numbers(self):
		for has_serial_no, has_batch_no in ((1, 0), (0, 1), (1, 1)):
			item = make_item(
				properties={"is_stock_item": 1, "has_serial_no": has_serial_no, "has_batch_no": has_batch_no}
			).name
			pr = self.make_draft_pr(item, qty=1)
			entry = {"qty": 1}
			if has_batch_no:
				batch = frappe.get_doc(doctype="Batch", item=item, batch_id="Export-Batch").insert()
				entry["batch_no"] = batch.name
			if has_serial_no:
				serial = frappe.get_doc(
					doctype="Serial No",
					item_code=item,
					serial_no="Export-Serial",
					batch_no=entry.get("batch_no"),
					company=pr.company,
				).insert()
				entry["serial_no"] = serial.name
			summary = self.upsert(pr, entries=[entry])
			with patch("frappe.utils.csvutils.build_csv_response") as response:
				download_bundle_entries_csv(summary.bundle)
			rows = response.call_args.args[0]
			expected = (["Export-Serial"] if has_serial_no else []) + (
				["Export-Batch", 1] if has_batch_no else []
			)
			self.assertEqual(rows[1], expected)
			stored = frappe.db.get_value(
				"Serial and Batch Entry", {"parent": summary.bundle}, ["serial_no", "batch_no"], as_dict=True
			)
			self.assertEqual(stored.serial_no or None, entry.get("serial_no"))
			self.assertEqual(stored.batch_no or None, entry.get("batch_no"))

	def test_selector_saves_physical_numbers_and_native_links(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		other = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		other_serial = self.make_serial(other, "Selector-Serial")
		selected = self.make_serial(item, "Selected-Serial")
		pr = self.make_draft_pr(item, qty=2)
		bundle = self.save_selector(
			pr, entries=[{"serial_no": selected}], csv_entries=[{"serial_no": "Selector-Serial", "qty": 1}]
		)
		bundle.reload()
		self.assertEqual(bundle.total_qty, 2)
		self.assertEqual(bundle.entries[0].serial_no, selected)
		serial = frappe.get_doc("Serial No", bundle.entries[1].serial_no)
		self.assertEqual((serial.item_code, serial.serial_no), (item, "Selector-Serial"))
		self.assertNotEqual(serial.name, other_serial)
		pr.items[0].serial_and_batch_bundle = bundle.name
		pr.items[0].type_of_transaction = "Outward"
		updated = self.save_selector(pr, csv_entries=[{"serial_no": "Replacement-Serial", "qty": 1}])
		self.assertEqual(updated.name, bundle.name)
		self.assertEqual(updated.total_qty, 1)
		self.assertEqual(
			frappe.db.get_value("Serial No", updated.entries[0].serial_no, "serial_no"), "Replacement-Serial"
		)

	def test_selector_outward_save_cannot_create_records(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		pr.is_return = 1
		pr.items[0].type_of_transaction = "Inward"
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			self.save_selector(pr, csv_entries=[{"serial_no": "Missing-Serial", "qty": 1}])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Serial"}))

	def test_selector_rejects_mismatched_bundle_context(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		other = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		bundle = self.save_selector(pr, csv_entries=[{"serial_no": "Selector-Serial", "qty": 1}])
		pr.items[0].serial_and_batch_bundle = bundle.name
		for mismatch in ("item", "company"):
			row = pr.items[0].as_dict()
			parent = pr.as_dict()
			if mismatch == "item":
				row.item_code = other
			else:
				parent.company = "_Test Company 1"
			with self.subTest(mismatch=mismatch), self.assertRaisesRegex(
				frappe.ValidationError, "same Item and Company"
			):
				add_serial_batch_ledgers(
					[], row, parent, csv_entries=[{"serial_no": "Missing-Serial", "qty": 1}]
				)
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Serial"}))
		bundle.reload()
		self.assertEqual(len(bundle.entries), 1)

	def test_selector_creation_follows_the_voucher_not_the_serial_master(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		user = frappe.get_doc(
			doctype="User",
			email="selector-stock-user@example.com",
			first_name="Selector",
			send_welcome_email=0,
			roles=[{"role": "Stock User"}],
		).insert()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			self.save_selector(pr, csv_entries=[{"serial_no": "Missing-Serial", "qty": 1}])
		self.assertTrue(frappe.db.exists("Serial No", {"item_code": item, "serial_no": "Missing-Serial"}))

	def test_pagination(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=5)
		serials = sorted(self.make_serial(item) for _ in range(5))

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		page = get_bundle_entries(summary.bundle, start=0, page_length=2)
		self.assertEqual(len(page["entries"]), 2)
		self.assertEqual(page["total_count"], 5)

		last_page = get_bundle_entries(summary.bundle, start=4, page_length=2)
		self.assertEqual(len(last_page["entries"]), 1)

	def test_search_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		token = frappe.generate_hash(length=8)
		serials = [self.make_serial(item, f"AAA-{token}"), self.make_serial(item, f"BBB-{token}")]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		page = get_bundle_entries(summary.bundle, search=f"aaa-{token}")
		self.assertEqual(len(page["entries"]), 1)
		self.assertEqual(page["entries"][0].serial_no, serials[0])
		self.assertEqual(get_bundle_entries(summary.bundle, search=serials[0])["entries"], [])

	def test_search_batches_by_physical_number(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		other_item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(doctype="Batch", item=item, batch_id="Physical-Lot").insert()
		frappe.get_doc(doctype="Batch", item=other_item, batch_id="Physical-Lot").insert()
		pr = self.make_draft_pr(item, qty=1)
		summary = self.upsert(pr, entries=[{"batch_no": batch.name, "qty": 1}])
		page = get_bundle_entries(summary.bundle, search="physical-lot")
		self.assertEqual(len(page["entries"]), 1)
		self.assertEqual(page["entries"][0].batch_no, batch.name)
		self.assertEqual(get_bundle_entries(summary.bundle, search=batch.name)["entries"], [])

	def test_rejected_bundle_created_separately(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		pr.items[0].rejected_warehouse = "_Test Warehouse 1 - _TC"

		accepted = self.upsert(pr, entries=[{"serial_no": self.make_serial(item)}])
		pr.items[0].serial_and_batch_bundle = accepted.bundle

		rejected = self.upsert(pr, entries=[{"serial_no": self.make_serial(item)}], is_rejected=1)

		self.assertNotEqual(accepted.bundle, rejected.bundle)
		bundle = frappe.get_doc("Serial and Batch Bundle", rejected.bundle)
		self.assertEqual(bundle.is_rejected, 1)
		self.assertEqual(bundle.warehouse, "_Test Warehouse 1 - _TC")

	def test_replace_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		old_serials = [self.make_serial(item) for _ in range(2)]
		new_serials = [self.make_serial(item) for _ in range(3)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in old_serials])
		pr.items[0].serial_and_batch_bundle = summary.bundle

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in new_serials], replace=1)

		self.assertEqual(summary.total_count, 3)
		remaining = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="serial_no")
		self.assertEqual(sorted(remaining), sorted(new_serials))

	def test_replace_with_no_entries_removes_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [self.make_serial(item) for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])
		bundle = summary.bundle
		pr.items[0].serial_and_batch_bundle = bundle

		summary = self.upsert(pr, entries=[], replace=1)

		self.assertFalse(summary.bundle)
		self.assertEqual(summary.total_count, 0)
		self.assertFalse(frappe.db.exists("Serial and Batch Bundle", bundle))

	def test_create_bundle_for_stock_entry(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		se = make_stock_entry(item_code=item, qty=2, to_warehouse="_Test Warehouse - _TC", do_not_submit=True)

		child_row = se.items[0].as_dict()
		child_row["is_rejected"] = 0
		summary = upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(se.as_dict(), default=str),
			entries=json.dumps([{"serial_no": self.make_serial(item)} for _ in range(2)]),
			deleted=json.dumps([]),
		)

		bundle = frappe.get_doc("Serial and Batch Bundle", summary.bundle)
		self.assertEqual(bundle.voucher_type, "Stock Entry")
		self.assertEqual(bundle.type_of_transaction, "Inward")
		self.assertEqual(summary.total_qty, 2)

	def test_upsert_requires_entries_for_new_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)

		self.assertRaises(frappe.ValidationError, self.upsert, pr)

	def test_upsert_rejects_mismatched_parenttype(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)

		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = 0
		child_row["parenttype"] = "Task"

		self.assertRaises(
			frappe.ValidationError,
			upsert_bundle_entries,
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			entries=json.dumps([{"serial_no": "SBIE-PT-0001"}]),
		)

	def test_upsert_rejects_unsupported_voucher_type(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)

		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = 0
		child_row["parenttype"] = "Task"

		doc = pr.as_dict()
		doc["doctype"] = "Task"

		self.assertRaises(
			frappe.ValidationError,
			upsert_bundle_entries,
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(doc, default=str),
			entries=json.dumps([{"serial_no": "SBIE-PT-0002"}]),
		)

	def make_serial(self, item_code, number=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"item_code": item_code,
					"serial_no": number or f"SN-{frappe.generate_hash(length=8)}",
					"company": "_Test Company",
				}
			)
			.insert()
			.name
		)
