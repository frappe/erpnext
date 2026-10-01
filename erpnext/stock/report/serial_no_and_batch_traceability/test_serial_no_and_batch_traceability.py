# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry import (
	get_fg_mapping,
	set_fg_mapping,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.serial_no_and_batch_traceability.serial_no_and_batch_traceability import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

SERIAL_ITEM = "_Test Serialized Item With Series"


class TestSerialNoAndBatchTraceability(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def get_received_serial_no(self, receipt):
		bundle = frappe.db.get_value(
			"Stock Entry Detail",
			{"parent": receipt.name, "item_code": SERIAL_ITEM},
			"serial_and_batch_bundle",
		)
		return frappe.db.get_value("Serial and Batch Entry", {"parent": bundle}, "serial_no")

	def test_serial_movements_traced(self):
		"""Backward trace should surface the receipt voucher the serial came in through."""
		receipt = make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)
		serial_no = self.get_received_serial_no(receipt)

		rows = self.run_report(
			item_code=SERIAL_ITEM,
			serial_nos=[serial_no],
			traceability_direction="Backward",
		)

		traced = {row["reference_name"]: row for row in rows if row.get("reference_name")}
		self.assertIn(receipt.name, traced)

		receipt_row = traced[receipt.name]
		self.assertEqual(receipt_row["serial_no"], serial_no)
		self.assertEqual(receipt_row["item_code"], SERIAL_ITEM)
		self.assertEqual(receipt_row["reference_doctype"], "Stock Entry")
		self.assertEqual(receipt_row["warehouse"], "Stores - _TC")
		self.assertEqual(receipt_row["direction"], "Backward")
		self.assertGreater(receipt_row["qty"], 0)

	def test_forward_and_backward_directions(self):
		"""'Both' should trace backward to the receipt and forward to the outward delivery."""
		receipt = make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)
		serial_no = self.get_received_serial_no(receipt)

		delivery_note = create_delivery_note(
			item_code=SERIAL_ITEM,
			qty=1,
			serial_no=[serial_no],
			warehouse="Stores - _TC",
			customer="_Test Customer",
			posting_date="2026-06-03",
			company="_Test Company",
		)

		rows = self.run_report(
			item_code=SERIAL_ITEM,
			serial_nos=[serial_no],
			traceability_direction="Both",
		)

		traced = {row["reference_name"]: row for row in rows if row.get("reference_name")}

		self.assertIn(receipt.name, traced)
		self.assertEqual(traced[receipt.name]["direction"], "Backward")

		self.assertIn(delivery_note.name, traced)
		forward_row = traced[delivery_note.name]
		self.assertEqual(forward_row["reference_doctype"], "Delivery Note")
		self.assertEqual(forward_row["serial_no"], serial_no)
		self.assertEqual(forward_row["direction"], "Forward")
		self.assertEqual(forward_row["customer"], delivery_note.customer)
		self.assertLess(forward_row["qty"], 0)

	def make_repack_with_serialized_items(self, fg_properties=None, fg_qty=3, extra_fg_items=None):
		rm_item = make_item(
			"_Test Traceability RM Serial Item",
			{"has_serial_no": 1, "serial_no_series": "TRC-RM-.#####", "is_stock_item": 1},
		).name

		fg_item_code = "_Test Traceability FG Serial Item"
		if fg_properties:
			fg_item_code = "_Test Traceability FG Batch Item"

		fg_item = make_item(
			fg_item_code,
			fg_properties or {"has_serial_no": 1, "serial_no_series": "TRC-FG-.#####", "is_stock_item": 1},
		).name

		make_stock_entry(
			item_code=rm_item, to_warehouse="Stores - _TC", qty=3, rate=100, company="_Test Company"
		)

		repack = make_stock_entry(
			item_code=rm_item,
			from_warehouse="Stores - _TC",
			qty=3,
			purpose="Repack",
			company="_Test Company",
			do_not_save=True,
		)
		for item_code, qty in [(fg_item, fg_qty), *(extra_fg_items or [])]:
			repack.append(
				"items",
				{
					"item_code": item_code,
					"qty": qty,
					"t_warehouse": "Finished Goods - _TC",
					"uom": "Nos",
					"stock_uom": "Nos",
					"conversion_factor": 1.0,
					# several finished goods need their rates set by hand
					"set_basic_rate_manually": 1 if extra_fg_items else 0,
					"basic_rate": 100,
				},
			)
		repack.save()
		repack.submit()

		mapping = get_fg_mapping(repack.name)
		return repack, fg_item, [row.value for row in mapping["fg_values"]], mapping["raw_materials"]

	def get_rm_serials_by_fg_serial(self, fg_item, fg_serial_nos):
		rows = self.run_report(item_code=fg_item, serial_nos=fg_serial_nos, traceability_direction="Backward")

		rm_serials_by_fg = {}
		current_fg = None
		for row in rows:
			if row.get("indent") == 0:
				current_fg = row.get("serial_no")
				rm_serials_by_fg.setdefault(current_fg, set())
			elif row.get("indent") == 1 and row.get("serial_no"):
				rm_serials_by_fg[current_fg].add(row["serial_no"])

		return rm_serials_by_fg

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_unmapped_fg_serial_shows_all_raw_material_serials(self):
		"""Without a mapping every FG serial traces back to the full pool of RM serials."""
		_repack, fg_item, fg_serial_nos, raw_materials = self.make_repack_with_serialized_items()
		rm_serial_nos = {row.serial_no for row in raw_materials}

		self.assertEqual(len(fg_serial_nos), 3)
		self.assertEqual(len(rm_serial_nos), 3)

		rm_serials_by_fg = self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos)
		for fg_serial_no in fg_serial_nos:
			self.assertEqual(rm_serials_by_fg[fg_serial_no], rm_serial_nos)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_mapped_fg_serial_shows_only_its_raw_material_serial(self):
		"""With a mapping each FG serial traces back to only its own RM serial, both directions."""
		repack, fg_item, fg_serial_nos, raw_materials = self.make_repack_with_serialized_items()

		expected = dict(zip(fg_serial_nos, [row.serial_no for row in raw_materials], strict=True))
		set_fg_mapping(
			repack.name,
			{row.name: fg_serial_no for row, fg_serial_no in zip(raw_materials, fg_serial_nos, strict=True)},
		)

		rm_serials_by_fg = self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos)
		for fg_serial_no, rm_serial_no in expected.items():
			self.assertEqual(rm_serials_by_fg[fg_serial_no], {rm_serial_no})

		fg_serial_no, rm_serial_no = next(iter(expected.items()))
		rows = self.run_report(
			item_code=raw_materials[0].item_code,
			serial_nos=[rm_serial_no],
			traceability_direction="Forward",
		)
		fg_rows = [row for row in rows if row.get("item_code") == fg_item]
		self.assertEqual([row["serial_no"] for row in fg_rows], [fg_serial_no])
		self.assertEqual(fg_rows[0]["qty"], 1)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_fg_serial_mapping_validations(self):
		repack, _fg_item, _fg_serial_nos, raw_materials = self.make_repack_with_serialized_items()

		self.assertRaises(
			frappe.ValidationError,
			set_fg_mapping,
			repack.name,
			{raw_materials[0].name: raw_materials[1].serial_no},
		)
		self.assertRaises(frappe.ValidationError, set_fg_mapping, repack.name, {"not-a-row": ""})

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_mapped_fg_batch_shows_its_raw_material_serials(self):
		"""Raw materials mapped to a finished good batch trace to that batch, both directions."""
		repack, fg_item, fg_batch_nos, raw_materials = self.make_repack_with_serialized_items(
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TRC-FGB-.#####",
				"is_stock_item": 1,
			}
		)
		self.assertEqual([row.fg_field for row in get_fg_mapping(repack.name)["fg_values"]], ["fg_batch_no"])
		self.assertEqual(len(fg_batch_nos), 1)

		fg_batch_no = fg_batch_nos[0]
		set_fg_mapping(repack.name, {row.name: fg_batch_no for row in raw_materials})
		self.assertEqual(
			{row.fg_batch_no for row in get_fg_mapping(repack.name)["raw_materials"]}, {fg_batch_no}
		)

		rows = self.run_report(item_code=fg_item, batches=[fg_batch_no], traceability_direction="Backward")
		self.assertEqual(
			{row["serial_no"] for row in rows if row.get("indent") == 1 and row.get("serial_no")},
			{row.serial_no for row in raw_materials},
		)

		rows = self.run_report(
			item_code=raw_materials[0].item_code,
			serial_nos=[raw_materials[0].serial_no],
			traceability_direction="Forward",
		)
		fg_rows = [row for row in rows if row.get("item_code") == fg_item]
		self.assertEqual([row["batch_no"] for row in fg_rows], [fg_batch_no])
		self.assertEqual(fg_rows[0]["qty"], 3)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_partly_mapped_entry_does_not_repeat_production(self):
		"""Unmapped raw materials of a partly mapped entry only carry the unmapped finished good qty."""
		repack, fg_item, fg_serial_nos, raw_materials = self.make_repack_with_serialized_items()
		set_fg_mapping(repack.name, {raw_materials[0].name: fg_serial_nos[0]})

		rows = self.run_report(item_code=raw_materials[0].item_code, traceability_direction="Forward")
		fg_rows = [
			row
			for row in rows
			if row.get("item_code") == fg_item and row.get("reference_name") == repack.name
		]

		self.assertEqual(
			sorted((row["serial_no"] or "", row["qty"]) for row in fg_rows), [("", 2), (fg_serial_nos[0], 1)]
		)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_mapping_to_second_finished_item(self):
		"""A Repack making a serialized and a batch tracked item offers both, and traces to the right item."""
		batch_fg_item = make_item(
			"_Test Traceability FG Batch Item",
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TRC-FGB-.#####",
				"is_stock_item": 1,
			},
		).name
		repack, serial_fg_item, _fg_values, _raw_materials = self.make_repack_with_serialized_items(
			fg_qty=2, extra_fg_items=[(batch_fg_item, 1)]
		)

		mapping = get_fg_mapping(repack.name)
		fg_fields = {row.item_code: row.fg_field for row in mapping["fg_values"]}
		self.assertEqual(fg_fields, {serial_fg_item: "fg_serial_no", batch_fg_item: "fg_batch_no"})

		batch_no = next(row.value for row in mapping["fg_values"] if row.item_code == batch_fg_item)
		raw_material = mapping["raw_materials"][0]
		set_fg_mapping(repack.name, {raw_material.name: batch_no})
		self.assertEqual(
			frappe.db.get_value("Serial and Batch Entry", raw_material.name, "fg_batch_no"), batch_no
		)

		rows = self.run_report(
			item_code=raw_material.item_code,
			serial_nos=[raw_material.serial_no],
			traceability_direction="Forward",
		)
		fg_rows = [row for row in rows if row.get("reference_name") == repack.name and row["indent"] == 0]
		self.assertEqual(
			[(row["item_code"], row["batch_no"], row["qty"]) for row in fg_rows],
			[(batch_fg_item, batch_no, 1)],
		)
