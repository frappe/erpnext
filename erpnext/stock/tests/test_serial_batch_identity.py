import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import (
	get_bundle_entries,
	upsert_bundle_entries,
)
from erpnext.stock.serial_batch_bundle import get_serial_or_batch_nos
from erpnext.stock.serial_batch_identity import (
	SerialBatchIdentity,
	resolve_number_entries,
	validate_item_merge,
)
from erpnext.stock.utils import scan_barcode
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchIdentity(ERPNextTestSuite):
	def make_item(self, serialized=False):
		return make_item(properties={"has_serial_no": int(serialized), "has_batch_no": int(not serialized)})

	def create_number(self, item, number, serialized=False):
		identity = SerialBatchIdentity("Serial No" if serialized else "Batch")
		return identity.resolve(item.name, [number], create=True, defaults={"company": "_Test Company"})[0]

	def test_numbers_are_unique_within_item(self):
		for serialized in (False, True):
			identity = SerialBatchIdentity("Serial No" if serialized else "Batch")
			items = [self.make_item(serialized) for _ in range(2)]
			number = frappe.generate_hash()
			ids = [self.create_number(item, number, serialized) for item in items]
			self.assertNotEqual(ids[0], ids[1])
			self.assertNotIn(number, ids)
			for item, name in zip(items, ids, strict=True):
				self.assertEqual(identity.resolve(item.name, [number]), [name])
				self.assertEqual(identity.resolve(item.name, [number], create=True), [name])
			duplicate = frappe.copy_doc(frappe.get_doc(identity.doctype, ids[0]))
			duplicate.set(identity.number_field, number)
			with self.assertRaises(frappe.DuplicateEntryError):
				duplicate.insert()

	def test_database_rejects_duplicate_even_without_controller_validation(self):
		for serialized in (False, True):
			item = self.make_item(serialized)
			name = self.create_number(item, frappe.generate_hash(), serialized)
			doctype = "Serial No" if serialized else "Batch"
			duplicate = frappe.get_doc(doctype, name)
			duplicate.name = frappe.generate_hash()
			frappe.db.savepoint("duplicate_number")
			try:
				with self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError)):
					duplicate.db_insert()
			finally:
				frappe.db.rollback(save_point="duplicate_number")

	def test_legacy_id_is_not_used_to_resolve_another_items_number(self):
		for serialized in (False, True):
			identity = SerialBatchIdentity("Serial No" if serialized else "Batch")
			old_item, new_item = self.make_item(serialized), self.make_item(serialized)
			old_id = self.create_number(old_item, frappe.generate_hash(), serialized)
			frappe.db.set_value(identity.doctype, old_id, identity.number_field, old_id)
			new_id = self.create_number(new_item, old_id, serialized)
			self.assertEqual(identity.resolve(old_item.name, [old_id]), [old_id])
			self.assertEqual(identity.resolve(new_item.name, [old_id]), [new_id])
			self.assertEqual(scan_barcode(old_id, {"item_code": new_item.name})["item_code"], new_item.name)

	def test_ambiguous_scan_and_new_match(self):
		for serialized in (False, True):
			items = [self.make_item(serialized) for _ in range(2)]
			number = frappe.generate_hash()
			self.create_number(items[0], number, serialized)
			self.assertEqual(scan_barcode(number)["item_code"], items[0].name)
			self.create_number(items[1], number, serialized)
			with self.assertRaises(frappe.ValidationError):
				scan_barcode(number)
			matches = scan_barcode(number, allow_multiple=True)["candidates"]
			self.assertEqual({row.item_code for row in matches}, {item.name for item in items})

	def test_receipts_store_ids_and_display_numbers(self):
		for serialized in (False, True):
			number = frappe.generate_hash()
			for item in [self.make_item(serialized) for _ in range(2)]:
				pr = make_purchase_receipt(item_code=item.name, qty=1, rate=100, do_not_submit=True)
				field = "serial_number" if serialized else "batch_number"
				link = "serial_no" if serialized else "batch_no"
				summary = upsert_bundle_entries(
					pr.items[0].as_dict(), pr.as_dict(), [{field: number, "qty": 1}]
				)
				pr.items[0].serial_and_batch_bundle = summary.bundle
				pr.save()
				pr.submit()
				rows = get_bundle_entries(summary.bundle)["entries"]
				self.assertNotEqual(rows[0][link], number)
				self.assertEqual(rows[0][field], number)
				self.assertIn(number, get_serial_or_batch_nos(summary.bundle))
				self.assertNotIn(rows[0][link], get_serial_or_batch_nos(summary.bundle))
				pr.cancel()

	def test_explicit_links_are_not_reinterpreted(self):
		item = self.make_item(True)
		name = self.create_number(item, frappe.generate_hash(), True)
		rows = [{"serial_no": name}]
		resolve_number_entries(item.name, rows)
		self.assertEqual(rows, [{"serial_no": name}])

	def test_item_merge_rejects_shared_numbers(self):
		for serialized in (False, True):
			items = [self.make_item(serialized) for _ in range(2)]
			number = frappe.generate_hash()
			for item in items:
				self.create_number(item, number, serialized)
			with self.assertRaises(frappe.ValidationError):
				validate_item_merge(items[0].name, items[1].name)

	def test_transfers_and_returns_keep_matching_numbers_separate(self):
		from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		for serialized in (False, True):
			items = [self.make_item(serialized) for _ in range(2)]
			number = frappe.generate_hash()
			ids = [self.create_number(item, number, serialized) for item in items]
			link = "serial_no" if serialized else "batch_no"
			receipts = []
			for item, name, rate in zip(items, ids, (11, 42), strict=True):
				receipts.append(
					make_purchase_receipt(
						item_code=item.name, qty=1, rate=rate, **{link: [name] if serialized else name}
					)
				)
			transfer = make_stock_entry(
				item_code=items[0].name,
				qty=1,
				from_warehouse="_Test Warehouse - _TC",
				to_warehouse="_Test Warehouse 1 - _TC",
				**{link: [ids[0]] if serialized else ids[0]},
			)
			if serialized:
				self.assertEqual(
					frappe.db.get_value("Serial No", ids[1], "warehouse"), "_Test Warehouse - _TC"
				)
			issue = make_stock_entry(
				item_code=items[0].name,
				qty=1,
				from_warehouse="_Test Warehouse 1 - _TC",
				**{link: [ids[0]] if serialized else ids[0]},
			)
			self.assertEqual(
				frappe.db.get_value(
					"Stock Ledger Entry",
					{"voucher_no": issue.name, "is_cancelled": 0},
					"stock_value_difference",
				),
				-11,
			)
			issue.cancel()
			transfer.cancel()
			purchase_return = make_purchase_return(receipts[0].name)
			purchase_return.insert().submit()
			if serialized:
				self.assertEqual(
					frappe.db.get_value("Serial No", ids[1], "warehouse"), "_Test Warehouse - _TC"
				)
			purchase_return.cancel()
			for receipt in receipts:
				receipt.cancel()

	def test_combined_serial_batch_csv_resolves_both_links(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			parse_csv_file_to_get_serial_batch,
		)

		item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		serials, batches = parse_csv_file_to_get_serial_batch(
			[["Serial No", "Batch No", "Quantity"], ["physical-serial", "physical-batch", "1"]]
		)
		resolve_number_entries(item.name, serials, create=True)
		resolve_number_entries(item.name, batches, create=True)
		self.assertEqual(serials[0]["batch_no"], batches[0]["batch_no"])
		self.assertNotEqual(serials[0]["serial_no"], "physical-serial")
		self.assertNotEqual(serials[0]["batch_no"], "physical-batch")

	def test_report_keeps_ids_and_exposes_physical_columns(self):
		from erpnext.stock.serial_batch_display import report_number_columns

		item = self.make_item(True)
		name = self.create_number(item, "physical-report-number", True)
		columns, rows = report_number_columns(
			[{"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No"}],
			[{"serial_no": name}],
		)
		self.assertEqual(rows[0]["serial_no"], name)
		self.assertEqual(rows[0]["serial_no_number"], "physical-report-number")
		self.assertEqual(columns[1]["hidden"], 1)
		self.assertFalse(columns[0]["hidden"])

	def test_migration_backfill_preserves_stock_references(self):
		for serialized in (False, True):
			identity = SerialBatchIdentity("Serial No" if serialized else "Batch")
			item = self.make_item(serialized)
			name = self.create_number(item, "legacy-number", serialized)
			link = "serial_no" if serialized else "batch_no"
			pr = make_purchase_receipt(
				item_code=item.name, qty=1, rate=100, **{link: [name] if serialized else name}
			)
			bundle = pr.items[0].serial_and_batch_bundle
			before = frappe.get_doc("Serial and Batch Bundle", bundle).as_dict()
			frappe.db.set_value(identity.doctype, name, identity.number_field, "")
			identity.backfill_numbers()
			identity.backfill_numbers()
			self.assertEqual(frappe.db.get_value(identity.doctype, name, identity.number_field), name)
			self.assertEqual(frappe.get_doc("Serial and Batch Bundle", bundle).as_dict(), before)
			pr.cancel()

	def test_print_formats_physical_serials_without_changing_stored_ids(self):
		from erpnext.stock.serial_batch_display import before_print

		item = self.make_item(True)
		name = self.create_number(item, "PRINT-123", True)
		pr = make_purchase_receipt(item_code=item.name, qty=1, rate=100, serial_no=[name])
		print_doc = frappe.get_doc("Purchase Receipt", pr.name)
		print_doc.items[0].serial_no = name
		before_print(print_doc)
		before_print(print_doc)
		self.assertEqual(print_doc.items[0].serial_no, name)
		self.assertIn("PRINT-123", print_doc.items[0].get_formatted("serial_no"))
		entry = frappe.get_doc("Serial and Batch Bundle", pr.items[0].serial_and_batch_bundle).entries[0]
		self.assertEqual(entry.serial_no, name)
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": "Serial Identity Test Print",
				"doc_type": "Purchase Receipt",
				"print_format_type": "Jinja",
				"custom_format": 1,
				"html": "{{ doc.items[0].get_formatted('serial_no') }}",
			}
		).insert()
		printed = frappe.get_print("Purchase Receipt", pr.name, print_format=print_format.name, doc=print_doc)
		self.assertEqual(print_doc.items[0].serial_no, name)
		self.assertIn("PRINT-123", printed)
		self.assertNotIn(name, printed)
		pr.cancel()

	def test_number_search_returns_ids_and_physical_titles(self):
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_number_options

		for serialized in (False, True):
			identity = SerialBatchIdentity("Serial No" if serialized else "Batch")
			item = self.make_item(serialized)
			name = self.create_number(item, "SEARCH-123", serialized)
			pr = make_purchase_receipt(
				item_code=item.name,
				qty=1,
				rate=100,
				**({"serial_no": [name]} if serialized else {"batch_no": name}),
			)
			for filters in ({"item_code": item.name}, {"voucher_no": [pr.name]}):
				options = get_number_options(identity.doctype, "SEARCH", 0, 20, filters)
				self.assertEqual([tuple(row) for row in options], [(name, "SEARCH-123")])
				self.assertEqual(
					[tuple(row) for row in get_number_options(identity.doctype, name, 0, 20, filters)],
					[(name, "SEARCH-123")],
				)
			pr.cancel()

	def test_combined_serial_batch_receipts_keep_items_separate(self):
		for _item in range(2):
			item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
			pr = make_purchase_receipt(item_code=item.name, qty=1, rate=100, do_not_submit=True)
			summary = upsert_bundle_entries(
				pr.items[0].as_dict(),
				pr.as_dict(),
				[{"serial_number": "COMBINED-SERIAL", "batch_number": "COMBINED-BATCH", "qty": 1}],
			)
			pr.items[0].serial_and_batch_bundle = summary.bundle
			pr.save().submit()
			entry = frappe.get_doc("Serial and Batch Bundle", summary.bundle).entries[0]
			self.assertNotEqual(entry.serial_no, "COMBINED-SERIAL")
			self.assertNotEqual(entry.batch_no, "COMBINED-BATCH")
			self.assertEqual(frappe.db.get_value("Serial No", entry.serial_no, "batch_no"), entry.batch_no)
			self.assertEqual(frappe.db.get_value("Batch", entry.batch_no, "item"), item.name)
			pr.cancel()

	def test_pos_search_returns_all_matching_items(self):
		from erpnext.selling.page.point_of_sale.point_of_sale import search_by_term

		for serialized in (False, True):
			items = [self.make_item(serialized) for _ in range(2)]
			number = "POS-" + frappe.generate_hash()
			ids = [self.create_number(item, number, serialized) for item in items]
			result = search_by_term(number, "_Test Warehouse - _TC", "Standard Selling")
			self.assertTrue(result["requires_selection"])
			self.assertEqual({row["item_code"] for row in result["items"]}, {item.name for item in items})
			field = "serial_no" if serialized else "batch_no"
			self.assertEqual({row[field] for row in result["items"]}, set(ids))

	def test_empty_batch_link_validation_accepts_the_resolved_id(self):
		from erpnext.controllers.queries import get_batch_no

		item = self.make_item()
		name = self.create_number(item, "EMPTY-BATCH")
		for text in ("EMPTY-BATCH", name):
			options = get_batch_no("Batch", text, "name", 0, 20, {"item_code": item.name, "is_inward": 1})
			self.assertEqual([(row[0], row[1]) for row in options], [(name, "EMPTY-BATCH")])
