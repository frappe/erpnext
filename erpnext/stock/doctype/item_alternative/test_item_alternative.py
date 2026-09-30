# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt, random_string

from erpnext.controllers.subcontracting_controller import make_rm_stock_entry
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_subcontracting_order,
	make_service_item,
	set_backflush_based_on,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.item_alternative.item_alternative import get_alternative_items
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	EmptyStockReconciliationItemsError,
)
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestItemAlternative(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		make_items()

	def test_alternative_item_for_subcontract_rm(self):
		set_backflush_based_on("BOM")

		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)

		supplier_warehouse = "Test Supplier Warehouse - _TC"

		make_service_item("Subcontracted Service Item 1")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 3000,
				"fg_item": "Test Finished Goods - A",
				"fg_item_qty": 5,
			},
		]
		sco = get_subcontracting_order(service_items=service_items, supplier_warehouse=supplier_warehouse)
		rm_items = [
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 1",
				"item_name": "Test FG A RW 1",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 2",
				"item_name": "Test FG A RW 2",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
		]

		reserved_qty_for_sub_contract = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_sub_contract",
		)

		se = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		se.to_warehouse = supplier_warehouse
		se.insert()

		doc = frappe.get_doc("Stock Entry", se.name)
		for item in doc.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"

		doc.save()
		doc.submit()
		after_transfer_reserved_qty_for_sub_contract = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_sub_contract",
		)

		self.assertEqual(after_transfer_reserved_qty_for_sub_contract, flt(reserved_qty_for_sub_contract - 5))

		scr = make_subcontracting_receipt(sco.name)
		scr.save()

		scr = frappe.get_doc("Subcontracting Receipt", scr.name)
		status = False
		for item in scr.supplied_items:
			if item.rm_item_code == "Alternate Item For A RW 1":
				status = True

		self.assertEqual(status, True)
		set_backflush_based_on("Material Transferred for Subcontract")

	def test_alternative_item_for_production_rm(self):
		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		pro_order = make_wo_order_test_record(
			production_item="Test Finished Goods - A",
			qty=5,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Test Supplier Warehouse - _TC",
		)

		reserved_qty_for_production = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_production",
		)

		ste = frappe.get_doc(make_stock_entry(pro_order.name, "Material Transfer for Manufacture", 5))
		ste.insert()

		for item in ste.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"

		ste.submit()
		reserved_qty_for_production_after_transfer = frappe.db.get_value(
			"Bin",
			{"item_code": "Test FG A RW 1", "warehouse": "_Test Warehouse - _TC"},
			"reserved_qty_for_production",
		)

		self.assertEqual(reserved_qty_for_production_after_transfer, flt(reserved_qty_for_production - 5))
		ste1 = frappe.get_doc(make_stock_entry(pro_order.name, "Manufacture", 5))

		status = False
		for d in ste1.items:
			if d.item_code == "Alternate Item For A RW 1":
				status = True

		self.assertEqual(status, True)
		ste1.submit()

	def test_get_used_alternative_items_returns_substitution(self):
		# get_used_alternative_items (raw SQL -> frappe.qb) returns the alternative items substituted
		# into a work order's transfer entries, keyed by the original item. Exercises the converted
		# query on both engines.
		from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items

		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		pro_order = make_wo_order_test_record(
			production_item="Test Finished Goods - A",
			qty=5,
			source_warehouse="_Test Warehouse - _TC",
			wip_warehouse="Test Supplier Warehouse - _TC",
		)

		ste = frappe.get_doc(make_stock_entry(pro_order.name, "Material Transfer for Manufacture", 5))
		ste.insert()
		for item in ste.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"
		ste.submit()

		used = get_used_alternative_items(work_order=pro_order.name)
		self.assertIn("Test FG A RW 1", used)
		self.assertEqual(used["Test FG A RW 1"].item_code, "Alternate Item For A RW 1")

	def test_get_used_alternative_items_for_subcontract_order(self):
		# Covers the subcontract_order branch of get_used_alternative_items (including the dynamic
		# subcontract_order_field column) on both engines.
		from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items

		set_backflush_based_on("BOM")
		create_stock_reconciliation(
			item_code="Alternate Item For A RW 1", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		create_stock_reconciliation(
			item_code="Test FG A RW 2", warehouse="_Test Warehouse - _TC", qty=5, rate=2000
		)
		supplier_warehouse = "Test Supplier Warehouse - _TC"
		make_service_item("Subcontracted Service Item 1")
		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 5,
				"rate": 3000,
				"fg_item": "Test Finished Goods - A",
				"fg_item_qty": 5,
			},
		]
		sco = get_subcontracting_order(service_items=service_items, supplier_warehouse=supplier_warehouse)
		rm_items = [
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 1",
				"item_name": "Test FG A RW 1",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
			{
				"item_code": "Test Finished Goods - A",
				"rm_item_code": "Test FG A RW 2",
				"item_name": "Test FG A RW 2",
				"qty": 5,
				"warehouse": "_Test Warehouse - _TC",
				"rate": 2000,
				"amount": 10000,
				"stock_uom": "Nos",
			},
		]

		se = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
		se.to_warehouse = supplier_warehouse
		se.insert()
		for item in se.items:
			if item.item_code == "Test FG A RW 1":
				item.item_code = "Alternate Item For A RW 1"
				item.item_name = "Alternate Item For A RW 1"
				item.description = "Alternate Item For A RW 1"
				item.original_item = "Test FG A RW 1"
		se.save()
		se.submit()

		used = get_used_alternative_items(
			subcontract_order=sco.name, subcontract_order_field="subcontracting_order"
		)
		self.assertIn("Test FG A RW 1", used)
		self.assertEqual(used["Test FG A RW 1"].item_code, "Alternate Item For A RW 1")
		set_backflush_based_on("Material Transferred for Subcontract")

	def test_get_alternative_items_both_directions_and_dedup(self):
		"""get_alternative_items must return forward alternatives, reverse-only
		two_way alternatives, exclude one-way reverse rows, and dedupe an item
		that matches in both the forward and reverse legs of the old UNION."""
		suffix = random_string(8)
		base = f"_Test IA Base {suffix}"
		alt_fwd = f"_Test IA Fwd {suffix}"  # forward only (two_way=0)
		alt_both = f"_Test IA Both {suffix}"  # forward (two_way=1)
		alt_rev = f"_Test IA Rev {suffix}"  # reverse via two_way=1
		alt_norev = f"_Test IA NoRev {suffix}"  # reverse but two_way=0 -> excluded
		dup = f"_Test IA Dup {suffix}"  # forward AND reverse -> must dedupe

		for item_code in (base, alt_fwd, alt_both, alt_rev, alt_norev, dup):
			create_item(item_code)
			item = frappe.get_doc("Item", item_code)
			if not item.allow_alternative_item:
				item.allow_alternative_item = 1
				item.save()

		# forward rows: item_code = base
		make_item_alternative(base, alt_fwd, two_way=0)
		make_item_alternative(base, alt_both, two_way=1)
		make_item_alternative(base, dup, two_way=1)

		# reverse rows: alternative_item_code = base
		make_item_alternative(alt_rev, base, two_way=1)
		make_item_alternative(alt_norev, base, two_way=0)
		make_item_alternative(dup, base, two_way=1)

		# txt = the shared suffix so the LIKE matches every alternate but not `base`
		results = get_alternative_items("Item", suffix, "name", 0, 20, {"item_code": base})

		# structure: list of single-element lists
		self.assertTrue(all(isinstance(row, list) and len(row) == 1 for row in results))

		returned = [row[0] for row in results]

		# forward alternatives (both one-way and two_way) are returned
		self.assertIn(alt_fwd, returned)
		self.assertIn(alt_both, returned)

		# reverse alternative is only returned when the row is two_way
		self.assertIn(alt_rev, returned)
		self.assertNotIn(alt_norev, returned)

		# `base` itself is never an alternative of itself
		self.assertNotIn(base, returned)

		# an item matching both legs of the old UNION is deduped to a single row
		self.assertIn(dup, returned)
		self.assertEqual(returned.count(dup), 1)

	def test_get_alternative_items_respects_txt_filter(self):
		"""The txt LIKE filter must actually narrow the result set so a
		non-matching alternate is excluded (guards against a broken WHERE)."""
		suffix = random_string(8)
		base = f"_Test IA Filter Base {suffix}"
		matching = f"_Test IA Match {suffix}"
		other = f"_Test IA Other {suffix}"

		for item_code in (base, matching, other):
			create_item(item_code)
			item = frappe.get_doc("Item", item_code)
			if not item.allow_alternative_item:
				item.allow_alternative_item = 1
				item.save()

		make_item_alternative(base, matching, two_way=0)
		make_item_alternative(base, other, two_way=0)

		# search only for the `Match` alternate
		results = get_alternative_items("Item", f"Match {suffix}", "name", 0, 20, {"item_code": base})
		returned = [row[0] for row in results]

		self.assertIn(matching, returned)
		self.assertNotIn(other, returned)

	def test_get_alternative_items_case_insensitive_match(self):
		"""The txt match must stay case-insensitive on BOTH engines: MariaDB LIKE is
		case-insensitive by default, and frappe compiles the `like` filter to ILIKE on
		Postgres. A case-shifted search must still find an alternate whose stored code
		differs in case — this guards against the conversion degrading to a case-sensitive
		match (plain LIKE / ==) that would silently return nothing on Postgres."""
		suffix = random_string(8)
		base = f"_Test IA Case Base {suffix}"
		# distinctive mixed-case token in the stored alternate's code
		alt = f"_Test IA CaseToken AbCdE {suffix}"

		for item_code in (base, alt):
			create_item(item_code)
			item = frappe.get_doc("Item", item_code)
			if not item.allow_alternative_item:
				item.allow_alternative_item = 1
				item.save()

		make_item_alternative(base, alt, two_way=0)

		# search the LOWERCASED token ("abcde") against the stored "AbCdE"
		results = get_alternative_items(
			"Item", f"casetoken abcde {suffix}", "name", 0, 20, {"item_code": base}
		)
		returned = [row[0] for row in results]

		self.assertIn(alt, returned)

	def test_get_alternative_items_pagination(self):
		"""start/page_len must slice the deduped, order-preserving result."""
		suffix = random_string(8)
		base = f"_Test IA Page Base {suffix}"
		alts = [f"_Test IA Page {i} {suffix}" for i in range(3)]

		create_item(base)
		base_item = frappe.get_doc("Item", base)
		if not base_item.allow_alternative_item:
			base_item.allow_alternative_item = 1
			base_item.save()

		for alt in alts:
			create_item(alt)
			alt_item = frappe.get_doc("Item", alt)
			if not alt_item.allow_alternative_item:
				alt_item.allow_alternative_item = 1
				alt_item.save()
			make_item_alternative(base, alt, two_way=0)

		full = [row[0] for row in get_alternative_items("Item", suffix, "name", 0, 20, {"item_code": base})]
		self.assertEqual(len(full), 3)

		page = [row[0] for row in get_alternative_items("Item", suffix, "name", 1, 1, {"item_code": base})]
		self.assertEqual(len(page), 1)
		self.assertEqual(page[0], full[1])

	def test_get_alternative_items_pagination_is_bounded_and_exact(self):
		"""Each get_all is bounded to start+page_len rows, so the DB round trip stays small
		instead of fetching every alternative per keystroke. Walking the result in small pages
		must still reconstruct the complete deduped set — including an alternate that appears in
		BOTH legs (forward + reverse two_way) — with no item dropped or duplicated by the bound."""
		suffix = random_string(8)
		base = f"_Test IA Bound Base {suffix}"
		forwards = [f"_Test IA Bound Fwd {i} {suffix}" for i in range(3)]
		reverses = [f"_Test IA Bound Rev {i} {suffix}" for i in range(3)]
		dup = f"_Test IA Bound Dup {suffix}"  # forward AND reverse two_way -> deduped across legs

		for item_code in [base, dup, *forwards, *reverses]:
			create_item(item_code)
			item = frappe.get_doc("Item", item_code)
			if not item.allow_alternative_item:
				item.allow_alternative_item = 1
				item.save()

		for fwd in forwards:
			make_item_alternative(base, fwd, two_way=0)
		make_item_alternative(base, dup, two_way=1)  # dup via the forward leg
		for rev in reverses:
			make_item_alternative(rev, base, two_way=1)
		make_item_alternative(dup, base, two_way=1)  # dup also via the reverse leg

		full = [row[0] for row in get_alternative_items("Item", suffix, "name", 0, 50, {"item_code": base})]
		# 3 forward + 3 reverse + the single deduped dup = 7 distinct
		self.assertEqual(len(full), 7)
		self.assertEqual(full.count(dup), 1)

		# walk in pages of 2; bounded fetches must yield exactly the same set, once each
		collected = []
		for start in range(0, 8, 2):
			collected += [
				row[0] for row in get_alternative_items("Item", suffix, "name", start, 2, {"item_code": base})
			]

		self.assertEqual(len(collected), len(set(collected)))  # no duplicates introduced by paging
		self.assertEqual(set(collected), set(full))  # nothing dropped by the per-leg limit
		self.assertEqual(collected.count(dup), 1)  # the cross-leg dup survives exactly once


def make_item_alternative(item_code, alternative_item_code, two_way=0):
	doc = frappe.get_doc(
		{
			"doctype": "Item Alternative",
			"item_code": item_code,
			"alternative_item_code": alternative_item_code,
			"two_way": two_way,
		}
	)
	doc.insert()
	return doc


def make_items():
	items = [
		"Test Finished Goods - A",
		"Test FG A RW 1",
		"Test FG A RW 2",
		"Alternate Item For A RW 1",
	]
	for item_code in items:
		if not frappe.db.exists("Item", item_code):
			create_item(item_code)

	try:
		create_stock_reconciliation(
			item_code="Test FG A RW 1", warehouse="_Test Warehouse - _TC", qty=10, rate=2000
		)
	except EmptyStockReconciliationItemsError:
		pass

	if frappe.db.exists("Item", "Test FG A RW 1"):
		doc = frappe.get_doc("Item", "Test FG A RW 1")
		doc.allow_alternative_item = 1
		doc.save()

	if frappe.db.exists("Item", "Test Finished Goods - A"):
		doc = frappe.get_doc("Item", "Test Finished Goods - A")
		doc.is_sub_contracted_item = 1
		doc.save()

	if not frappe.db.get_value("BOM", {"item": "Test Finished Goods - A", "docstatus": 1}):
		make_bom(item="Test Finished Goods - A", raw_materials=["Test FG A RW 1", "Test FG A RW 2"])

	if not frappe.db.get_value("Warehouse", {"warehouse_name": "Test Supplier Warehouse"}):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Supplier Warehouse",
				"company": "_Test Company",
			}
		).insert(ignore_permissions=True)
