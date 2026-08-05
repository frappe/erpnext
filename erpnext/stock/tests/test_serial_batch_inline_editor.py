# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
	get_voucher_entries,
	has_bundled_entries,
)
from erpnext.stock.serial_batch_inline_editor import (
	get_ledger_entries,
	upsert_bundle_entries,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchInlineEditor(ERPNextTestSuite):
	def make_draft_pr(self, item_code, qty=2):
		return make_purchase_receipt(item_code=item_code, qty=qty, rate=100, do_not_submit=True)

	def upsert(self, pr, entries=None, deleted=None, is_rejected=0, replace=0):
		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = is_rejected

		return upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			entries=json.dumps(entries or []),
			deleted=json.dumps(deleted or []),
			replace=replace,
		)

	def ledger_rows(self, pr, warehouse=None, fields=None):
		return get_voucher_entries(
			"Purchase Receipt",
			pr.name,
			pr.items[0].name,
			warehouse or pr.items[0].warehouse,
			fields=fields,
		)

	def reload_row(self, pr):
		pr.reload()
		return pr.items[0]

	def test_create_bundle_with_serials(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		self.assertTrue(
			has_bundled_entries("Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse)
		)
		self.assertEqual(summary.total_count, 2)
		self.assertEqual(summary.total_qty, 2)
		for serial_no in serials:
			self.assertTrue(frappe.db.exists("Serial No", serial_no))

	def test_incremental_append_preserves_existing_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(3)]

		self.upsert(pr, entries=[{"serial_no": serials[0]}, {"serial_no": serials[1]}])
		first_serials = {row.serial_no for row in self.ledger_rows(pr, fields=["serial_no"])}

		summary = self.upsert(pr, entries=[{"serial_no": serials[2]}])
		second_serials = {row.serial_no for row in self.ledger_rows(pr, fields=["serial_no"])}

		self.assertEqual(summary.total_count, 3)
		self.assertTrue(first_serials.issubset(second_serials))

	def test_delete_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		to_delete = [
			row.name
			for row in self.ledger_rows(pr, fields=["name", "serial_no"])
			if row.serial_no == serials[0]
		]
		summary = self.upsert(pr, deleted=to_delete)

		self.assertEqual(summary.total_count, 1)
		remaining = [row.serial_no for row in self.ledger_rows(pr, fields=["serial_no"])]
		self.assertEqual(remaining, [serials[1]])

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
		self.assertEqual(summary.total_qty, 5)

		entry_name = self.ledger_rows(pr)[0].name
		summary = self.upsert(pr, entries=[{"name": entry_name, "qty": 8}])

		self.assertEqual(summary.total_qty, 8)
		self.assertEqual(summary.total_count, 1)

	def test_update_serial_no_of_existing_entry(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		old_serial = f"SN-{frappe.generate_hash(length=8)}"
		new_serial = f"SN-{frappe.generate_hash(length=8)}"

		self.upsert(pr, entries=[{"serial_no": old_serial}])
		entry_name = self.ledger_rows(pr)[0].name

		self.upsert(pr, entries=[{"name": entry_name, "serial_no": new_serial}])

		remaining = [row.serial_no for row in self.ledger_rows(pr, fields=["serial_no"])]
		self.assertEqual(remaining, [new_serial])
		self.assertTrue(frappe.db.exists("Serial No", new_serial))

	def test_auto_create_missing_batch_no(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		pr = self.make_draft_pr(item, qty=5)
		batch1 = f"BNEW-{frappe.generate_hash(length=8)}"
		batch2 = f"BNEW-{frappe.generate_hash(length=8)}"

		self.assertFalse(frappe.db.exists("Batch", batch1))
		summary = self.upsert(pr, entries=[{"batch_no": batch1, "qty": 4}])
		self.assertTrue(frappe.db.exists("Batch", batch1))

		summary = self.upsert(pr, entries=[{"batch_no": batch2, "qty": 1}])

		self.assertTrue(frappe.db.exists("Batch", batch2))
		self.assertEqual(summary.total_qty, 5)

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

		self.upsert(pr, entries=[{"batch_no": batch1.name, "qty": 5}])

		entry_name = self.ledger_rows(pr)[0].name
		self.upsert(pr, entries=[{"name": entry_name, "batch_no": batch2.name}])

		entry = self.ledger_rows(pr, fields=["batch_no", "qty"])[0]
		self.assertEqual(entry.batch_no, batch2.name)
		self.assertEqual(abs(entry.qty), 5)

	def test_delete_all_entries_removes_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		to_delete = [row.name for row in self.ledger_rows(pr)]
		summary = self.upsert(pr, deleted=to_delete)

		self.assertFalse(summary.get("has_entries"))
		self.assertEqual(summary.total_count, 0)
		self.assertFalse(
			has_bundled_entries("Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse)
		)

	def test_remove_empty_bundle_ignores_spoofed_child_row(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		victim_pr = self.make_draft_pr(item)

		self.upsert(pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}])
		victim_summary = self.upsert(
			victim_pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}]
		)

		child_row = pr.items[0].as_dict()
		child_row["is_rejected"] = 0
		child_row["name"] = victim_pr.items[0].name

		to_delete = [row.name for row in self.ledger_rows(pr)]
		upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(pr.as_dict(), default=str),
			deleted=json.dumps(to_delete),
		)

		self.assertEqual(victim_summary.total_count, 1)
		self.assertTrue(
			has_bundled_entries(
				"Purchase Receipt", victim_pr.name, victim_pr.items[0].name, victim_pr.items[0].warehouse
			)
		)

	def test_pagination(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=5)
		serials = sorted(f"SN-{frappe.generate_hash(length=8)}" for _ in range(5))

		self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		page = get_ledger_entries(
			"Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse, start=0, page_length=2
		)
		self.assertEqual(len(page["entries"]), 2)
		self.assertEqual(page["total_count"], 5)

		last_page = get_ledger_entries(
			"Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse, start=4, page_length=2
		)
		self.assertEqual(len(last_page["entries"]), 1)

	def test_search_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		token = frappe.generate_hash(length=8)
		serials = [f"AAA-{token}", f"BBB-{token}"]

		self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		page = get_ledger_entries(
			"Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse, search=f"AAA-{token}"
		)
		self.assertEqual(len(page["entries"]), 1)
		self.assertEqual(page["entries"][0].serial_no, f"AAA-{token}")

	def test_rejected_bundle_created_separately(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		pr.items[0].rejected_warehouse = "_Test Warehouse 1 - _TC"

		accepted = self.upsert(pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}])
		rejected = self.upsert(
			pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}], is_rejected=1
		)

		self.assertEqual(accepted.total_count, 1)
		self.assertEqual(rejected.total_count, 1)

		accepted_rows = self.ledger_rows(pr, warehouse=pr.items[0].warehouse)
		rejected_rows = self.ledger_rows(pr, warehouse="_Test Warehouse 1 - _TC")
		self.assertEqual(len(accepted_rows), 1)
		self.assertEqual(len(rejected_rows), 1)
		self.assertNotEqual(accepted_rows[0].name, rejected_rows[0].name)

	def test_replace_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		old_serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]
		new_serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(3)]

		self.upsert(pr, entries=[{"serial_no": d} for d in old_serials])

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in new_serials], replace=1)

		self.assertEqual(summary.total_count, 3)
		remaining = [row.serial_no for row in self.ledger_rows(pr, fields=["serial_no"])]
		self.assertEqual(sorted(remaining), sorted(new_serials))

	def test_replace_with_no_entries_removes_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		summary = self.upsert(pr, entries=[], replace=1)

		self.assertFalse(summary.get("has_entries"))
		self.assertEqual(summary.total_count, 0)
		self.assertFalse(
			has_bundled_entries("Purchase Receipt", pr.name, pr.items[0].name, pr.items[0].warehouse)
		)

	def test_create_bundle_for_stock_entry(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		se = make_stock_entry(item_code=item, qty=2, to_warehouse="_Test Warehouse - _TC", do_not_submit=True)

		child_row = se.items[0].as_dict()
		child_row["is_rejected"] = 0
		summary = upsert_bundle_entries(
			child_row=json.dumps(child_row, default=str),
			doc=json.dumps(se.as_dict(), default=str),
			entries=json.dumps([{"serial_no": f"SN-{frappe.generate_hash(length=8)}"} for _ in range(2)]),
			deleted=json.dumps([]),
		)

		entries = get_voucher_entries(
			"Stock Entry", se.name, se.items[0].name, se.items[0].t_warehouse, fields=["type_of_transaction"]
		)
		self.assertEqual(len(entries), 2)
		self.assertTrue(all(entry.type_of_transaction == "Inward" for entry in entries))
		self.assertEqual(summary.total_qty, 2)

	def test_upsert_requires_entries_for_new_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)

		summary = self.upsert(pr)

		self.assertFalse(summary.get("has_entries"))
		self.assertEqual(summary.total_count, 0)

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
