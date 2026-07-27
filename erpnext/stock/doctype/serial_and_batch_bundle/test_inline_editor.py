# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import (
	get_bundle_entries,
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

	def reload_row(self, pr):
		pr.reload()
		return pr.items[0]

	def test_create_bundle_with_serials(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		self.assertTrue(frappe.db.exists("Serial and Batch Bundle", summary.bundle))
		self.assertEqual(summary.total_count, 2)
		self.assertEqual(summary.total_qty, 2)
		for serial_no in serials:
			self.assertTrue(frappe.db.exists("Serial No", serial_no))

	def test_incremental_append_preserves_existing_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(3)]

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
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])
		pr.items[0].serial_and_batch_bundle = summary.bundle

		to_delete = frappe.get_all(
			"Serial and Batch Entry", {"parent": summary.bundle, "serial_no": serials[0]}, pluck="name"
		)
		summary = self.upsert(pr, deleted=to_delete)

		self.assertEqual(summary.total_count, 1)
		remaining = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="serial_no")
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
		pr.items[0].serial_and_batch_bundle = summary.bundle
		self.assertEqual(summary.total_qty, 5)

		entry_name = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")[0]
		summary = self.upsert(pr, entries=[{"name": entry_name, "qty": 8}])

		self.assertEqual(summary.total_qty, 8)
		self.assertEqual(summary.total_count, 1)

	def test_update_serial_no_of_existing_entry(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=1)
		old_serial = f"SN-{frappe.generate_hash(length=8)}"
		new_serial = f"SN-{frappe.generate_hash(length=8)}"

		summary = self.upsert(pr, entries=[{"serial_no": old_serial}])
		pr.items[0].serial_and_batch_bundle = summary.bundle
		entry_name = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="name")[0]

		self.upsert(pr, entries=[{"name": entry_name, "serial_no": new_serial}])

		self.assertEqual(frappe.db.get_value("Serial and Batch Entry", entry_name, "serial_no"), new_serial)
		self.assertTrue(frappe.db.exists("Serial No", new_serial))

	def test_auto_create_missing_batch_no(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		pr = self.make_draft_pr(item, qty=5)
		batch1 = f"BNEW-{frappe.generate_hash(length=8)}"
		batch2 = f"BNEW-{frappe.generate_hash(length=8)}"

		self.assertFalse(frappe.db.exists("Batch", batch1))
		summary = self.upsert(pr, entries=[{"batch_no": batch1, "qty": 4}])
		self.assertTrue(frappe.db.exists("Batch", batch1))

		pr.items[0].serial_and_batch_bundle = summary.bundle
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
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

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

		summary = self.upsert(pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}])
		bundle = summary.bundle
		pr.items[0].db_set("serial_and_batch_bundle", bundle)

		victim_summary = self.upsert(
			victim_pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}]
		)
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

	def test_pagination(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=5)
		serials = sorted(f"SN-{frappe.generate_hash(length=8)}" for _ in range(5))

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
		serials = [f"AAA-{token}", f"BBB-{token}"]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in serials])

		page = get_bundle_entries(summary.bundle, search=f"AAA-{token}")
		self.assertEqual(len(page["entries"]), 1)
		self.assertEqual(page["entries"][0].serial_no, f"AAA-{token}")

	def test_rejected_bundle_created_separately(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		pr.items[0].rejected_warehouse = "_Test Warehouse 1 - _TC"

		accepted = self.upsert(pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}])
		pr.items[0].serial_and_batch_bundle = accepted.bundle

		rejected = self.upsert(
			pr, entries=[{"serial_no": f"SN-{frappe.generate_hash(length=8)}"}], is_rejected=1
		)

		self.assertNotEqual(accepted.bundle, rejected.bundle)
		bundle = frappe.get_doc("Serial and Batch Bundle", rejected.bundle)
		self.assertEqual(bundle.is_rejected, 1)
		self.assertEqual(bundle.warehouse, "_Test Warehouse 1 - _TC")

	def test_replace_entries(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item, qty=3)
		old_serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]
		new_serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(3)]

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in old_serials])
		pr.items[0].serial_and_batch_bundle = summary.bundle

		summary = self.upsert(pr, entries=[{"serial_no": d} for d in new_serials], replace=1)

		self.assertEqual(summary.total_count, 3)
		remaining = frappe.get_all("Serial and Batch Entry", {"parent": summary.bundle}, pluck="serial_no")
		self.assertEqual(sorted(remaining), sorted(new_serials))

	def test_replace_with_no_entries_removes_bundle(self):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name
		pr = self.make_draft_pr(item)
		serials = [f"SN-{frappe.generate_hash(length=8)}" for _ in range(2)]

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
			entries=json.dumps([{"serial_no": f"SN-{frappe.generate_hash(length=8)}"} for _ in range(2)]),
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
