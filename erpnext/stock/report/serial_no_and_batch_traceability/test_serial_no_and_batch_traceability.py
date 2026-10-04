# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry import (
	get_fg_mapping,
	get_fg_quotas,
	get_fg_target,
	get_fg_values,
	get_raw_material_entries,
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

	def make_rm_item(self, batch=False):
		if batch:
			return make_item(
				"_Test Traceability RM Batch Item",
				{
					"has_batch_no": 1,
					"create_new_batch": 1,
					"batch_number_series": "TRC-RMB-.#####",
					"is_stock_item": 1,
				},
			).name

		return make_item(
			"_Test Traceability RM Serial Item",
			{"has_serial_no": 1, "serial_no_series": "TRC-RM-.#####", "is_stock_item": 1},
		).name

	def make_fg_item(self, batch=False):
		if batch:
			return make_item(
				"_Test Traceability FG Batch Item",
				{
					"has_batch_no": 1,
					"create_new_batch": 1,
					"batch_number_series": "TRC-FGB-.#####",
					"is_stock_item": 1,
				},
			).name

		return make_item(
			"_Test Traceability FG Serial Item",
			{"has_serial_no": 1, "serial_no_series": "TRC-FG-.#####", "is_stock_item": 1},
		).name

	def receive(self, item_code, qty=3):
		receipt = make_stock_entry(
			item_code=item_code, to_warehouse="Stores - _TC", qty=qty, rate=100, company="_Test Company"
		)
		return frappe.get_all(
			"Serial and Batch Entry",
			{"parent": receipt.items[0].serial_and_batch_bundle},
			pluck="serial_no",
		)

	def make_repack(self, raw_materials, finished_goods, submit=True):
		"""raw_materials / finished_goods: [(item_code, qty, serial nos for a user created bundle or None)]"""
		repack = frappe.new_doc("Stock Entry")
		repack.update({"purpose": "Repack", "stock_entry_type": "Repack", "company": "_Test Company"})

		for item_code, qty, serial_nos in raw_materials:
			repack.append(
				"items",
				{
					"item_code": item_code,
					"qty": qty,
					"s_warehouse": "Stores - _TC",
					"uom": "Nos",
					"stock_uom": "Nos",
					"conversion_factor": 1.0,
					"serial_and_batch_bundle": serial_nos
					and self.make_bundle(item_code, "Stores - _TC", -qty, serial_nos),
				},
			)

		for item_code, qty, serial_nos in finished_goods:
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
					"set_basic_rate_manually": 1 if len(finished_goods) > 1 else 0,
					"basic_rate": 100,
					"serial_and_batch_bundle": serial_nos
					and self.make_bundle(item_code, "Finished Goods - _TC", qty, serial_nos),
				},
			)

		repack.save()
		if submit:
			repack.submit()

		return repack

	def make_bundle(self, item_code, warehouse, qty, serial_nos):
		"""A bundle the user creates first and links to the draft entry."""
		return make_serial_batch_bundle(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": qty,
				"rate": 100,
				"serial_nos": serial_nos,
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"do_not_submit": True,
			}
		).name

	def new_fg_serial_nos(self, item_code, qty=3):
		"""Serial nos the user creates for the finished goods; the site's naming decides their names."""
		return [
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": f"TRC-FGM-{frappe.generate_hash(length=8).upper()}",
					"item_code": item_code,
					"company": "_Test Company",
				}
			)
			.insert()
			.name
			for _ in range(qty)
		]

	def get_rm_serials_by_fg_serial(self, fg_item, fg_serial_nos):
		rows = self.run_report(item_code=fg_item, serial_nos=fg_serial_nos, traceability_direction="Backward")

		rm_serials_by_fg = {}
		current_fg = None
		for row in rows:
			if row.get("indent") == 0:
				current_fg = row.get("serial_no")
				rm_serials_by_fg.setdefault(current_fg, set())
			elif row.get("indent") == 1 and (row.get("serial_no") or row.get("batch_no")):
				rm_serials_by_fg[current_fg].add(row.get("serial_no") or row.get("batch_no"))

		return rm_serials_by_fg

	def get_forward_fg_rows(self, item_code, repack, **filters):
		rows = self.run_report(item_code=item_code, traceability_direction="Forward", **filters)
		return [row for row in rows if row.get("reference_name") == repack.name and row["indent"] == 0]

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 1},
	)
	def test_auto_mapping_on_submit(self):
		"""Auto created bundles: each finished good serial gets one raw material serial, in order."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		rm_serial_nos = self.receive(rm_item)
		repack = self.make_repack([(rm_item, 3, None)], [(fg_item, 3, None)])

		fg_serial_nos = [row.value for row in get_fg_values(repack.name)]
		raw_materials = get_raw_material_entries(repack.name)
		self.assertEqual({row.serial_no for row in raw_materials}, set(rm_serial_nos))
		# in the order the raw material serial nos were picked
		self.assertEqual([row.fg_serial_no for row in raw_materials], fg_serial_nos)

		rm_serials_by_fg = self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos)
		for row in raw_materials:
			self.assertEqual(rm_serials_by_fg[row.fg_serial_no], {row.serial_no})

	def test_draft_mapping_is_kept_on_submit(self):
		"""User created bundles are mapped on draft; the mapping is kept and locked on submit."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		rm_serial_nos = self.receive(rm_item)
		fg_serial_nos = self.new_fg_serial_nos(fg_item)
		repack = self.make_repack([(rm_item, 3, rm_serial_nos)], [(fg_item, 3, fg_serial_nos)], submit=False)

		mapping = get_fg_mapping(repack.name)
		self.assertEqual([row.value for row in mapping["fg_values"]], fg_serial_nos)

		# map in reverse order, so it differs from what the auto mapping would do
		expected = dict(zip(rm_serial_nos, reversed(fg_serial_nos), strict=True))
		set_fg_mapping(repack.name, {row.name: expected[row.serial_no] for row in mapping["raw_materials"]})

		repack.reload()
		repack.submit()

		raw_materials = get_raw_material_entries(repack.name)
		self.assertEqual({row.serial_no: row.fg_serial_no for row in raw_materials}, expected)
		self.assertRaises(frappe.ValidationError, set_fg_mapping, repack.name, {raw_materials[0].name: None})

		rm_serials_by_fg = self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos)
		for rm_serial_no, fg_serial_no in expected.items():
			self.assertEqual(rm_serials_by_fg[fg_serial_no], {rm_serial_no})

		fg_rows = self.get_forward_fg_rows(rm_item, repack, serial_nos=[rm_serial_nos[0]])
		self.assertEqual(
			[(row["serial_no"], row["qty"]) for row in fg_rows], [(expected[rm_serial_nos[0]], 1)]
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"auto_map_raw_materials_to_finished_goods": 1})
	def test_partly_mapped_draft_is_completed_on_submit(self):
		"""Raw materials left unmapped on draft are mapped to the remaining finished goods on submit."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		rm_serial_nos = self.receive(rm_item)
		fg_serial_nos = self.new_fg_serial_nos(fg_item)
		repack = self.make_repack([(rm_item, 3, rm_serial_nos)], [(fg_item, 3, fg_serial_nos)], submit=False)

		# the bundle row order is what the mapping on submit follows
		raw_materials = get_fg_mapping(repack.name)["raw_materials"]
		rm_serial_nos = [row.serial_no for row in raw_materials]
		set_fg_mapping(repack.name, {raw_materials[0].name: fg_serial_nos[2]})

		repack.reload()
		repack.submit()

		self.assertEqual(
			{row.serial_no: row.fg_serial_no for row in get_raw_material_entries(repack.name)},
			{
				rm_serial_nos[0]: fg_serial_nos[2],
				rm_serial_nos[1]: fg_serial_nos[0],
				rm_serial_nos[2]: fg_serial_nos[1],
			},
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"auto_map_raw_materials_to_finished_goods": 0})
	def test_draft_mapping_kept_when_auto_mapping_is_disabled(self):
		"""With auto mapping off, the draft mapping is kept and the rest is left unmapped."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		rm_serial_nos = self.receive(rm_item)
		fg_serial_nos = self.new_fg_serial_nos(fg_item)
		repack = self.make_repack([(rm_item, 3, rm_serial_nos)], [(fg_item, 3, fg_serial_nos)], submit=False)

		# the bundle row order is what the mapping on submit follows
		raw_materials = get_fg_mapping(repack.name)["raw_materials"]
		rm_serial_nos = [row.serial_no for row in raw_materials]
		set_fg_mapping(repack.name, {raw_materials[0].name: fg_serial_nos[2]})

		repack.reload()
		repack.submit()

		self.assertEqual(
			{row.serial_no: row.fg_serial_no for row in get_raw_material_entries(repack.name)},
			{rm_serial_nos[0]: fg_serial_nos[2], rm_serial_nos[1]: None, rm_serial_nos[2]: None},
		)

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 0},
	)
	def test_unmapped_raw_materials_can_be_mapped_after_submit(self):
		"""Auto created bundles get their raw material rows on submit, so the rows left unmapped can be mapped then."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		self.receive(rm_item)
		repack = self.make_repack([(rm_item, 3, None)], [(fg_item, 3, None)])

		mapping = get_fg_mapping(repack.name)
		fg_serial_nos = [row.value for row in mapping["fg_values"]]
		raw_materials = mapping["raw_materials"]
		self.assertEqual([row.fg_serial_no for row in raw_materials], [None, None, None])

		set_fg_mapping(repack.name, {raw_materials[0].name: fg_serial_nos[2]})
		set_fg_mapping(
			repack.name,
			{raw_materials[1].name: fg_serial_nos[0], raw_materials[2].name: fg_serial_nos[1]},
		)

		expected = {
			raw_materials[0].serial_no: fg_serial_nos[2],
			raw_materials[1].serial_no: fg_serial_nos[0],
			raw_materials[2].serial_no: fg_serial_nos[1],
		}
		self.assertEqual(
			{row.serial_no: row.fg_serial_no for row in get_raw_material_entries(repack.name)}, expected
		)

		# a mapped raw material is fixed once the entry is submitted
		self.assertRaises(
			frappe.ValidationError, set_fg_mapping, repack.name, {raw_materials[0].name: fg_serial_nos[0]}
		)
		self.assertRaises(frappe.ValidationError, set_fg_mapping, repack.name, {raw_materials[0].name: None})

		rm_serials_by_fg = self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos)
		for rm_serial_no, fg_serial_no in expected.items():
			self.assertEqual(rm_serials_by_fg[fg_serial_no], {rm_serial_no})

		repack.cancel()
		self.assertRaises(frappe.ValidationError, get_fg_mapping, repack.name)

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 1},
	)
	def test_auto_mapping_to_fg_batch(self):
		"""A single finished good batch takes every raw material, both directions."""
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item(batch=True)
		rm_serial_nos = self.receive(rm_item)
		repack = self.make_repack([(rm_item, 3, None)], [(fg_item, 3, None)])

		fg_values = get_fg_values(repack.name)
		self.assertEqual([row.fg_field for row in fg_values], ["fg_batch_no"])
		fg_batch_no = fg_values[0].value
		self.assertEqual({row.fg_batch_no for row in get_raw_material_entries(repack.name)}, {fg_batch_no})

		rows = self.run_report(item_code=fg_item, batches=[fg_batch_no], traceability_direction="Backward")
		self.assertEqual(
			{row["serial_no"] for row in rows if row.get("indent") == 1 and row.get("serial_no")},
			set(rm_serial_nos),
		)

		fg_rows = self.get_forward_fg_rows(rm_item, repack, serial_nos=[rm_serial_nos[0]])
		self.assertEqual([(row["batch_no"], row["qty"]) for row in fg_rows], [(fg_batch_no, 3)])

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 1},
	)
	def test_auto_mapping_across_serial_and_batch_finished_goods(self):
		"""A Repack making a serialized and a batch tracked item maps across both, to the right item."""
		rm_item = self.make_rm_item()
		serial_fg_item, batch_fg_item = self.make_fg_item(), self.make_fg_item(batch=True)
		self.receive(rm_item)
		repack = self.make_repack([(rm_item, 3, None)], [(serial_fg_item, 2, None), (batch_fg_item, 1, None)])

		fg_values = get_fg_values(repack.name)
		self.assertEqual(
			[(row.item_code, row.fg_field) for row in fg_values],
			[
				(serial_fg_item, "fg_serial_no"),
				(serial_fg_item, "fg_serial_no"),
				(batch_fg_item, "fg_batch_no"),
			],
		)

		raw_materials = get_raw_material_entries(repack.name)
		self.assertEqual(
			[row.fg_serial_no or row.fg_batch_no for row in raw_materials],
			[row.value for row in fg_values],
		)

		# the last picked raw material went into the batch tracked finished good
		fg_rows = self.get_forward_fg_rows(rm_item, repack, serial_nos=[raw_materials[2].serial_no])
		self.assertEqual(
			[(row["item_code"], row["batch_no"], row["qty"]) for row in fg_rows],
			[(batch_fg_item, fg_values[2].value, 1)],
		)

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 1},
	)
	def test_auto_mapping_follows_finished_good_qty(self):
		"""A finished good batch of 3 takes three times the raw material serials of a single finished good serial."""
		# 5 raw material serials split 1.25 / 3.75, so the leftover one goes to the batch, not the serial
		for rm_qty, expected_counts in ((4, (1, 3)), (5, (1, 4))):
			with self.subTest(rm_qty=rm_qty):
				rm_item = self.make_rm_item()
				serial_fg_item, batch_fg_item = self.make_fg_item(), self.make_fg_item(batch=True)
				self.receive(rm_item, qty=rm_qty)
				repack = self.make_repack(
					[(rm_item, rm_qty, None)], [(serial_fg_item, 1, None), (batch_fg_item, 3, None)]
				)

				fg_values = get_fg_values(repack.name)
				self.assertEqual(
					[(row.fg_field, row.qty) for row in fg_values], [("fg_serial_no", 1), ("fg_batch_no", 3)]
				)

				raw_materials = get_raw_material_entries(repack.name)
				self.assertEqual(
					[row.fg_serial_no or row.fg_batch_no for row in raw_materials],
					[fg_values[0].value] * expected_counts[0] + [fg_values[1].value] * expected_counts[1],
				)

	def test_fg_quotas(self):
		targets = ["a", "b", "c"]
		for count, fg_qty, expected in (
			(5, {"a": 1, "b": 3}, {"a": 1, "b": 4}),
			(4, {"a": 1, "b": 3}, {"a": 1, "b": 3}),
			(5, {"a": 1, "b": 1, "c": 1}, {"a": 2, "b": 2, "c": 1}),
			(2, {"a": 1, "b": 1, "c": 1}, {"a": 1, "b": 1, "c": 0}),
			(3, {"a": 2.5, "b": 0.5}, {"a": 3, "b": 0}),
		):
			fg_targets = [target for target in targets if target in fg_qty]
			with self.subTest(count=count, fg_qty=fg_qty):
				quotas = get_fg_quotas(count, fg_targets, fg_qty)
				self.assertEqual(quotas, expected)
				self.assertEqual(sum(quotas.values()), count)

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"auto_create_serial_and_batch_bundle_for_outward": 1, "auto_map_raw_materials_to_finished_goods": 1},
	)
	def test_batch_raw_material_stays_with_every_finished_good(self):
		"""A batch used across several finished good serials is not auto mapped to just one of them."""
		rm_item, batch_rm_item, fg_item = (
			self.make_rm_item(),
			self.make_rm_item(batch=True),
			self.make_fg_item(),
		)
		self.receive(rm_item)
		self.receive(batch_rm_item)
		rm_batch_no = frappe.get_all(
			"Batch", {"item": batch_rm_item}, pluck="name", order_by="creation desc"
		)[0]

		repack = self.make_repack([(rm_item, 3, None), (batch_rm_item, 3, None)], [(fg_item, 3, None)])
		fg_serial_nos = [row.value for row in get_fg_values(repack.name)]

		batch_entries = [
			row for row in get_raw_material_entries(repack.name) if row.item_code == batch_rm_item
		]
		self.assertEqual([(row.fg_serial_no, row.fg_batch_no) for row in batch_entries], [(None, None)])

		for rm_values in self.get_rm_serials_by_fg_serial(fg_item, fg_serial_nos).values():
			self.assertIn(rm_batch_no, rm_values)

		# the serialized raw material is fully mapped, which must not shrink the batch's finished goods
		fg_rows = self.get_forward_fg_rows(batch_rm_item, repack, batches=[rm_batch_no])
		self.assertEqual([(row["serial_no"], row["qty"]) for row in fg_rows], [(None, 3)])

	def test_fg_mapping_validations(self):
		rm_item, fg_item = self.make_rm_item(), self.make_fg_item()
		rm_serial_nos = self.receive(rm_item)
		repack = self.make_repack(
			[(rm_item, 3, rm_serial_nos)], [(fg_item, 3, self.new_fg_serial_nos(fg_item))], submit=False
		)
		raw_materials = get_fg_mapping(repack.name)["raw_materials"]

		# a raw material serial is not a finished good of the entry
		self.assertRaises(
			frappe.ValidationError,
			set_fg_mapping,
			repack.name,
			{raw_materials[0].name: raw_materials[1].serial_no},
		)
		self.assertRaises(frappe.ValidationError, set_fg_mapping, repack.name, {"not-a-row": ""})

		# the mapping must be a dictionary, also when sent as JSON
		self.assertRaises(
			frappe.ValidationError, set_fg_mapping, repack.name, frappe.as_json([raw_materials[0].name])
		)

		# a bundle that belongs to another voucher can't be changed through this entry
		bundle = frappe.db.get_value("Serial and Batch Entry", raw_materials[0].name, "parent")
		frappe.db.set_value("Serial and Batch Bundle", bundle, "voucher_no", "MAT-STE-OTHER")
		self.assertRaises(frappe.ValidationError, set_fg_mapping, repack.name, {raw_materials[0].name: None})

	def test_fg_target_with_shared_serial_and_batch_name(self):
		"""A serial no and a batch no with the same name are kept apart."""
		fg_targets = {("fg_serial_no", "FG-001"), ("fg_batch_no", "FG-001"), ("fg_batch_no", "B-1")}

		self.assertEqual(get_fg_target("B-1", fg_targets, "SE"), ("fg_batch_no", "B-1"))
		self.assertEqual(
			get_fg_target({"fg_field": "fg_batch_no", "value": "FG-001"}, fg_targets, "SE"),
			("fg_batch_no", "FG-001"),
		)
		self.assertEqual(
			get_fg_target({"fg_field": "fg_serial_no", "value": "FG-001"}, fg_targets, "SE"),
			("fg_serial_no", "FG-001"),
		)
		self.assertEqual(get_fg_target(None, fg_targets, "SE"), (None, None))
		self.assertRaises(frappe.ValidationError, get_fg_target, "FG-001", fg_targets, "SE")
		self.assertRaises(
			frappe.ValidationError,
			get_fg_target,
			{"fg_field": "fg_serial_no", "value": "B-1"},
			fg_targets,
			"SE",
		)
