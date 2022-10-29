# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import deque
from functools import partial

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cstr, flt

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.manufacturing.doctype.bom.bom import BOMRecursionError, item_query
from erpnext.manufacturing.doctype.bom_update_log.test_bom_update_log import (
	update_cost_in_all_boms_in_test,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.tests.test_subcontracting import set_backflush_based_on

test_records = frappe.get_test_records("BOM")
test_dependencies = ["Item", "Quality Inspection Template"]


class TestBOM(FrappeTestCase):
	def test_get_items(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		items_dict = get_bom_items_as_dict(
			bom=get_default_bom(), company="_Test Company", qty=1, fetch_exploded=0
		)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertEqual(len(items_dict.values()), 2)

	def test_get_items_exploded(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		items_dict = get_bom_items_as_dict(
			bom=get_default_bom(), company="_Test Company", qty=1, fetch_exploded=1
		)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertFalse(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][1]["item_code"] in items_dict)
		self.assertEqual(len(items_dict.values()), 3)

	def test_get_items_list(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items

		self.assertEqual(len(get_bom_items(bom=get_default_bom(), company="_Test Company")), 3)

	def test_default_bom(self):
		def _get_default_bom_in_item():
			return cstr(frappe.db.get_value("Item", "_Test FG Item 2", "default_bom"))

		bom = frappe.get_doc("BOM", {"item": "_Test FG Item 2", "is_default": 1})
		self.assertEqual(_get_default_bom_in_item(), bom.name)

		bom.is_active = 0
		bom.save()
		self.assertEqual(_get_default_bom_in_item(), "")

		bom.is_active = 1
		bom.is_default = 1
		bom.save()

		self.assertTrue(_get_default_bom_in_item(), bom.name)

	def test_update_bom_cost_in_all_boms(self):
		# get current rate for '_Test Item 2'
		bom_rates = frappe.db.get_values(
			"BOM Item",
			{
				"parent": "BOM-_Test Item Home Desktop Manufactured-001",
				"item_code": "_Test Item 2",
				"docstatus": 1,
			},
			fieldname=["rate", "base_rate"],
			as_dict=True,
		)
		rm_base_rate = bom_rates[0].get("base_rate") if bom_rates else 0

		# Reset item valuation rate
		reset_item_valuation_rate(item_code="_Test Item 2", qty=200, rate=rm_base_rate + 10)

		# update cost of all BOMs based on latest valuation rate
		update_cost_in_all_boms_in_test()

		# check if new valuation rate updated in all BOMs
		for d in frappe.db.sql(
			"""select base_rate from `tabBOM Item`
			where item_code='_Test Item 2' and docstatus=1 and parenttype='BOM'""",
			as_dict=1,
		):
			self.assertEqual(d.base_rate, rm_base_rate + 10)

	def test_bom_cost(self):
		bom = frappe.copy_doc(test_records[2])
		bom.insert()

		raw_material_cost = 0.0
		op_cost = 0.0

		for op_row in bom.operations:
			op_cost += op_row.operating_cost

		for row in bom.items:
			raw_material_cost += row.amount

		base_raw_material_cost = raw_material_cost * flt(
			bom.conversion_rate, bom.precision("conversion_rate")
		)
		base_op_cost = op_cost * flt(bom.conversion_rate, bom.precision("conversion_rate"))

		# test amounts in selected currency, almostEqual checks for 7 digits by default
		self.assertAlmostEqual(bom.operating_cost, op_cost)
		self.assertAlmostEqual(bom.raw_material_cost, raw_material_cost)
		self.assertAlmostEqual(bom.total_cost, raw_material_cost + op_cost)

		# test amounts in selected currency
		self.assertAlmostEqual(bom.base_operating_cost, base_op_cost)
		self.assertAlmostEqual(bom.base_raw_material_cost, base_raw_material_cost)
		self.assertAlmostEqual(bom.base_total_cost, base_raw_material_cost + base_op_cost)

	def test_bom_cost_with_batch_size(self):
		bom = frappe.copy_doc(test_records[2])
		bom.docstatus = 0
		op_cost = 0.0
		for op_row in bom.operations:
			op_row.docstatus = 0
			op_row.batch_size = 2
			op_row.set_cost_based_on_bom_qty = 1
			op_cost += op_row.operating_cost

		bom.save()

		for op_row in bom.operations:
			self.assertAlmostEqual(op_row.cost_per_unit, op_row.operating_cost / 2)

		self.assertAlmostEqual(bom.operating_cost, op_cost / 2)
		bom.delete()

	def test_bom_cost_multi_uom_multi_currency_based_on_price_list(self):
		frappe.db.set_value("Price List", "_Test Price List", "price_not_uom_dependent", 1)
		for item_code, rate in (("_Test Item", 3600), ("_Test Item Home Desktop Manufactured", 3000)):
			frappe.db.sql(
				"delete from `tabItem Price` where price_list='_Test Price List' and item_code=%s", item_code
			)
			item_price = frappe.new_doc("Item Price")
			item_price.price_list = "_Test Price List"
			item_price.item_code = item_code
			item_price.price_list_rate = rate
			item_price.insert()

		bom = frappe.copy_doc(test_records[2])
		bom.set_rate_of_sub_assembly_item_based_on_bom = 0
		bom.rm_cost_as_per = "Price List"
		bom.buying_price_list = "_Test Price List"
		bom.items[0].uom = "_Test UOM 1"
		bom.items[0].conversion_factor = 5
		bom.insert()

		bom.update_cost(update_hour_rate=False)

		# test amounts in selected currency
		self.assertEqual(bom.items[0].rate, 300)
		self.assertEqual(bom.items[1].rate, 50)
		self.assertEqual(bom.operating_cost, 100)
		self.assertEqual(bom.raw_material_cost, 450)
		self.assertEqual(bom.total_cost, 550)

		# test amounts in selected currency
		self.assertEqual(bom.items[0].base_rate, 18000)
		self.assertEqual(bom.items[1].base_rate, 3000)
		self.assertEqual(bom.base_operating_cost, 6000)
		self.assertEqual(bom.base_raw_material_cost, 27000)
		self.assertEqual(bom.base_total_cost, 33000)

	def test_bom_cost_multi_uom_based_on_valuation_rate(self):
		bom = frappe.copy_doc(test_records[2])
		bom.set_rate_of_sub_assembly_item_based_on_bom = 0
		bom.rm_cost_as_per = "Valuation Rate"
		bom.items[0].uom = "_Test UOM 1"
		bom.items[0].conversion_factor = 6
		bom.insert()

		reset_item_valuation_rate(
			item_code="_Test Item",
			warehouse_list=frappe.get_all(
				"Warehouse", {"is_group": 0, "company": bom.company}, pluck="name"
			),
			qty=200,
			rate=200,
		)

		bom.update_cost()

		self.assertEqual(bom.items[0].rate, 20)

	def test_subcontractor_sourced_item(self):
		item_code = "_Test Subcontracted FG Item 1"
		set_backflush_based_on("Material Transferred for Subcontract")

		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"is_stock_item": 1, "is_sub_contracted_item": 1, "stock_uom": "Nos"})

		if not frappe.db.exists("Item", "Test Extra Item 1"):
			make_item("Test Extra Item 1", {"is_stock_item": 1, "stock_uom": "Nos"})

		if not frappe.db.exists("Item", "Test Extra Item 2"):
			make_item("Test Extra Item 2", {"is_stock_item": 1, "stock_uom": "Nos"})

		if not frappe.db.exists("Item", "Test Extra Item 3"):
			make_item("Test Extra Item 3", {"is_stock_item": 1, "stock_uom": "Nos"})
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"is_default": 1,
				"item": item_code,
				"currency": "USD",
				"quantity": 1,
				"company": "_Test Company",
			}
		)

		for item in ["Test Extra Item 1", "Test Extra Item 2"]:
			item_doc = frappe.get_doc("Item", item)

			bom.append(
				"items",
				{
					"item_code": item,
					"qty": 1,
					"uom": item_doc.stock_uom,
					"stock_uom": item_doc.stock_uom,
					"rate": item_doc.valuation_rate,
				},
			)

		bom.append(
			"items",
			{
				"item_code": "Test Extra Item 3",
				"qty": 1,
				"uom": item_doc.stock_uom,
				"stock_uom": item_doc.stock_uom,
				"rate": 0,
				"sourced_by_supplier": 1,
			},
		)
		bom.insert(ignore_permissions=True)
		bom.update_cost()
		bom.submit()
		# test that sourced_by_supplier rate is zero even after updating cost
		self.assertEqual(bom.items[2].rate, 0)
		# test in Purchase Order sourced_by_supplier is not added to Supplied Item
		po = create_purchase_order(
			item_code=item_code, qty=1, is_subcontracted="Yes", supplier_warehouse="_Test Warehouse 1 - _TC"
		)
		bom_items = sorted([d.item_code for d in bom.items if d.sourced_by_supplier != 1])
		supplied_items = sorted([d.rm_item_code for d in po.supplied_items])
		self.assertEqual(bom_items, supplied_items)

	def test_bom_recursion_1st_level(self):
		"""BOM should not allow BOM item again in child"""
		item_code = make_item(properties={"is_stock_item": 1}).name

		bom = frappe.new_doc("BOM")
		bom.item = item_code
		bom.append("items", frappe._dict(item_code=item_code))
		bom.save()
		with self.assertRaises(BOMRecursionError):
			bom.items[0].bom_no = bom.name
			bom.save()

	def test_bom_recursion_transitive(self):
		item1 = make_item(properties={"is_stock_item": 1}).name
		item2 = make_item(properties={"is_stock_item": 1}).name

		bom1 = frappe.new_doc("BOM")
		bom1.item = item1
		bom1.append("items", frappe._dict(item_code=item2))
		bom1.save()

		bom2 = frappe.new_doc("BOM")
		bom2.item = item2
		bom2.append("items", frappe._dict(item_code=item1))
		bom2.save()

		bom2.items[0].bom_no = bom1.name
		bom1.items[0].bom_no = bom2.name

		with self.assertRaises(BOMRecursionError):
			bom1.save()
			bom2.save()

	def test_bom_with_process_loss_item(self):
		fg_item_non_whole, fg_item_whole, bom_item = create_process_loss_bom_items()

		if not frappe.db.exists("BOM", f"BOM-{fg_item_non_whole.item_code}-001"):
			bom_doc = create_bom_with_process_loss_item(
				fg_item_non_whole, bom_item, scrap_qty=0.25, scrap_rate=0, fg_qty=1
			)
			bom_doc.submit()

		bom_doc = create_bom_with_process_loss_item(
			fg_item_non_whole, bom_item, scrap_qty=2, scrap_rate=0
		)
		#  PL Item qty can't be >= FG Item qty
		self.assertRaises(frappe.ValidationError, bom_doc.submit)

		bom_doc = create_bom_with_process_loss_item(
			fg_item_non_whole, bom_item, scrap_qty=1, scrap_rate=100
		)
		# PL Item rate has to be 0
		self.assertRaises(frappe.ValidationError, bom_doc.submit)

		bom_doc = create_bom_with_process_loss_item(
			fg_item_whole, bom_item, scrap_qty=0.25, scrap_rate=0
		)
		#  Items with whole UOMs can't be PL Items
		self.assertRaises(frappe.ValidationError, bom_doc.submit)

		bom_doc = create_bom_with_process_loss_item(
			fg_item_non_whole, bom_item, scrap_qty=0.25, scrap_rate=0, is_process_loss=0
		)
		# FG Items in Scrap/Loss Table should have Is Process Loss set
		self.assertRaises(frappe.ValidationError, bom_doc.submit)

	def test_bom_tree_representation(self):
		bom_tree = {
			"Assembly": {
				"SubAssembly1": {
					"ChildPart1": {},
					"ChildPart2": {},
				},
				"SubAssembly2": {"ChildPart3": {}},
				"SubAssembly3": {"SubSubAssy1": {"ChildPart4": {}}},
				"ChildPart5": {},
				"ChildPart6": {},
				"SubAssembly4": {"SubSubAssy2": {"ChildPart7": {}}},
			}
		}
		parent_bom = create_nested_bom(bom_tree, prefix="")
		created_tree = parent_bom.get_tree_representation()

		reqd_order = level_order_traversal(bom_tree)[1:]  # skip first item
		created_order = created_tree.level_order_traversal()

		self.assertEqual(len(reqd_order), len(created_order))

		for reqd_item, created_item in zip(reqd_order, created_order):
			self.assertEqual(reqd_item, created_item.item_code)

	def test_bom_item_query(self):
		query = partial(
			item_query,
			doctype="Item",
			txt="",
			searchfield="name",
			start=0,
			page_len=20,
			filters={"is_stock_item": 1},
		)

		test_items = query(txt="_Test")
		filtered = query(txt="_Test Item 2")

		self.assertNotEqual(
			len(test_items), len(filtered), msg="Item filtering showing excessive results"
		)
		self.assertTrue(0 < len(filtered) <= 3, msg="Item filtering showing excessive results")

	def test_valid_transfer_defaults(self):
		bom_with_op = frappe.db.get_value(
			"BOM", {"item": "_Test FG Item 2", "with_operations": 1, "is_active": 1}
		)
		bom = frappe.copy_doc(frappe.get_doc("BOM", bom_with_op), ignore_no_copy=False)

		# test defaults
		bom.docstatus = 0
		bom.transfer_material_against = None
		bom.insert()
		self.assertEqual(bom.transfer_material_against, "Work Order")

		bom.reload()
		bom.transfer_material_against = None
		with self.assertRaises(frappe.ValidationError):
			bom.save()
		bom.reload()

		# test saner default
		bom.transfer_material_against = "Job Card"
		bom.with_operations = 0
		bom.save()
		self.assertEqual(bom.transfer_material_against, "Work Order")

		# test no value on existing doc
		bom.transfer_material_against = None
		bom.with_operations = 0
		bom.save()
		self.assertEqual(bom.transfer_material_against, "Work Order")
		bom.delete()

	def test_bom_name_length(self):
		"""test >140 char names"""
		bom_tree = {"x" * 140: {" ".join(["abc"] * 35): {}}}
		create_nested_bom(bom_tree, prefix="")

	def test_version_index(self):

		bom = frappe.new_doc("BOM")

		version_index_test_cases = [
			(1, []),
			(1, ["BOM#XYZ"]),
			(2, ["BOM/ITEM/001"]),
			(2, ["BOM-ITEM-001"]),
			(3, ["BOM-ITEM-001", "BOM-ITEM-002"]),
			(4, ["BOM-ITEM-001", "BOM-ITEM-002", "BOM-ITEM-003"]),
		]

		for expected_index, existing_boms in version_index_test_cases:
			with self.subTest():
				self.assertEqual(
					expected_index,
					bom.get_next_version_index(existing_boms),
					msg=f"Incorrect index for {existing_boms}",
				)

	def test_bom_versioning(self):
		bom_tree = {frappe.generate_hash(length=10): {frappe.generate_hash(length=10): {}}}
		bom = create_nested_bom(bom_tree, prefix="")
		self.assertEqual(int(bom.name.split("-")[-1]), 1)
		original_bom_name = bom.name

		bom.cancel()
		bom.reload()
		self.assertEqual(bom.name, original_bom_name)

		# create a new amendment
		amendment = frappe.copy_doc(bom)
		amendment.docstatus = 0
		amendment.amended_from = bom.name

		amendment.save()
		amendment.submit()
		amendment.reload()

		self.assertNotEqual(amendment.name, bom.name)
		# `origname-001-1` version
		self.assertEqual(int(amendment.name.split("-")[-1]), 1)
		self.assertEqual(int(amendment.name.split("-")[-2]), 1)

		# create a new version
		version = frappe.copy_doc(amendment)
		version.docstatus = 0
		version.amended_from = None
		version.save()
		self.assertNotEqual(amendment.name, version.name)
		self.assertEqual(int(version.name.split("-")[-1]), 2)

	def test_clear_inpection_quality(self):

		bom = frappe.copy_doc(test_records[2], ignore_no_copy=True)
		bom.docstatus = 0
		bom.is_default = 0
		bom.quality_inspection_template = "_Test Quality Inspection Template"
		bom.inspection_required = 1
		bom.save()
		bom.reload()

		self.assertEqual(bom.quality_inspection_template, "_Test Quality Inspection Template")

		bom.inspection_required = 0
		bom.save()
		bom.reload()

		self.assertEqual(bom.quality_inspection_template, None)

	def test_bom_pricing_based_on_lpp(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		parent = frappe.generate_hash(length=10)
		child = frappe.generate_hash(length=10)
		bom_tree = {parent: {child: {}}}
		bom = create_nested_bom(bom_tree, prefix="")

		# add last purchase price
		make_purchase_receipt(item_code=child, rate=42)

		bom = frappe.copy_doc(bom)
		bom.docstatus = 0
		bom.amended_from = None
		bom.rm_cost_as_per = "Last Purchase Rate"
		bom.conversion_rate = 1
		bom.save()
		bom.submit()
		self.assertEqual(bom.items[0].rate, 42)

	def test_exclude_exploded_items_from_bom(self):
		bom_no = get_default_bom()
		new_bom = frappe.copy_doc(frappe.get_doc("BOM", bom_no))
		for row in new_bom.items:
			if row.item_code == "_Test Item Home Desktop Manufactured":
				self.assertTrue(row.bom_no)
				row.do_not_explode = True

		new_bom.docstatus = 0
		new_bom.save()
		new_bom.load_from_db()

		for row in new_bom.items:
			if row.item_code == "_Test Item Home Desktop Manufactured" and row.do_not_explode:
				self.assertFalse(row.bom_no)

		new_bom.delete()

	def test_set_default_bom_for_item_having_single_bom(self):
		from erpnext.stock.doctype.item.test_item import make_item

		fg_item = make_item(properties={"is_stock_item": 1})
		bom_item = make_item(properties={"is_stock_item": 1})

		# Step 1: Create BOM
		bom = frappe.new_doc("BOM")
		bom.item = fg_item.item_code
		bom.quantity = 1
		bom.append(
			"items",
			{
				"item_code": bom_item.item_code,
				"qty": 1,
				"uom": bom_item.stock_uom,
				"stock_uom": bom_item.stock_uom,
				"rate": 100.0,
			},
		)
		bom.save()
		bom.submit()
		self.assertEqual(frappe.get_value("Item", fg_item.item_code, "default_bom"), bom.name)

		# Step 2: Uncheck is_active field
		bom.is_active = 0
		bom.save()
		bom.reload()
		self.assertIsNone(frappe.get_value("Item", fg_item.item_code, "default_bom"))

		# Step 3: Check is_active field
		bom.is_active = 1
		bom.save()
		bom.reload()
		self.assertEqual(frappe.get_value("Item", fg_item.item_code, "default_bom"), bom.name)

	def test_exploded_items_rate(self):
		rm_item = make_item(
			properties={"is_stock_item": 1, "valuation_rate": 99, "last_purchase_rate": 89}
		).name
		fg_item = make_item(properties={"is_stock_item": 1}).name

		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		bom = make_bom(item=fg_item, raw_materials=[rm_item], do_not_save=True)

		bom.rm_cost_as_per = "Last Purchase Rate"
		bom.save()
		self.assertEqual(bom.items[0].base_rate, 89)
		self.assertEqual(bom.exploded_items[0].rate, bom.items[0].base_rate)

		bom.rm_cost_as_per = "Price List"
		bom.save()
		self.assertEqual(bom.items[0].base_rate, 0.0)
		self.assertEqual(bom.exploded_items[0].rate, bom.items[0].base_rate)

		bom.rm_cost_as_per = "Valuation Rate"
		bom.save()
		self.assertEqual(bom.items[0].base_rate, 99)
		self.assertEqual(bom.exploded_items[0].rate, bom.items[0].base_rate)

		bom.submit()
		self.assertEqual(bom.exploded_items[0].rate, bom.items[0].base_rate)

	def test_bom_cost_update_flag(self):
		rm_item = make_item(
			properties={"is_stock_item": 1, "valuation_rate": 99, "last_purchase_rate": 89}
		).name
		fg_item = make_item(properties={"is_stock_item": 1}).name

		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		bom = make_bom(item=fg_item, raw_materials=[rm_item])

		create_stock_reconciliation(
			item_code=rm_item, warehouse="_Test Warehouse - _TC", qty=100, rate=600
		)

		bom.load_from_db()
		bom.update_cost()
		self.assertTrue(bom.flags.cost_updated)

		bom.load_from_db()
		bom.update_cost()
		self.assertFalse(bom.flags.cost_updated)


def get_default_bom(item_code="_Test FG Item 2"):
	return frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "is_default": 1})


def level_order_traversal(node):
	traversal = []
	q = deque()
	q.append(node)

	while q:
		node = q.popleft()

		for node_name, subtree in node.items():
			traversal.append(node_name)
			q.append(subtree)

	return traversal


def create_nested_bom(tree, prefix="_Test bom "):
	"""Helper function to create a simple nested bom from tree describing item names. (along with required items)"""

	def create_items(bom_tree):
		for item_code, subtree in bom_tree.items():
			bom_item_code = prefix + item_code
			if not frappe.db.exists("Item", bom_item_code):
				frappe.get_doc(doctype="Item", item_code=bom_item_code, item_group="_Test Item Group").insert()
			create_items(subtree)

	create_items(tree)

	def dfs(tree, node):
		"""naive implementation for searching right subtree"""
		for node_name, subtree in tree.items():
			if node_name == node:
				return subtree
			else:
				result = dfs(subtree, node)
				if result is not None:
					return result

	order_of_creating_bom = reversed(level_order_traversal(tree))

	for item in order_of_creating_bom:
		child_items = dfs(tree, item)
		if child_items:
			bom_item_code = prefix + item
			bom = frappe.get_doc(doctype="BOM", item=bom_item_code)
			for child_item in child_items.keys():
				bom.append("items", {"item_code": prefix + child_item})
			bom.company = "_Test Company"
			bom.currency = "INR"
			bom.insert()
			bom.submit()

	return bom  # parent bom is last bom


def reset_item_valuation_rate(item_code, warehouse_list=None, qty=None, rate=None):
	if warehouse_list and isinstance(warehouse_list, str):
		warehouse_list = [warehouse_list]

	if not warehouse_list:
		warehouse_list = frappe.db.sql_list(
			"""
			select warehouse from `tabBin`
			where item_code=%s and actual_qty > 0
		""",
			item_code,
		)

		if not warehouse_list:
			warehouse_list.append("_Test Warehouse - _TC")

	for warehouse in warehouse_list:
		create_stock_reconciliation(item_code=item_code, warehouse=warehouse, qty=qty, rate=rate)


def create_bom_with_process_loss_item(
	fg_item, bom_item, scrap_qty, scrap_rate, fg_qty=2, is_process_loss=1
):
	bom_doc = frappe.new_doc("BOM")
	bom_doc.item = fg_item.item_code
	bom_doc.quantity = fg_qty
	bom_doc.append(
		"items",
		{
			"item_code": bom_item.item_code,
			"qty": 1,
			"uom": bom_item.stock_uom,
			"stock_uom": bom_item.stock_uom,
			"rate": 100.0,
		},
	)
	bom_doc.append(
		"scrap_items",
		{
			"item_code": fg_item.item_code,
			"qty": scrap_qty,
			"stock_qty": scrap_qty,
			"uom": fg_item.stock_uom,
			"stock_uom": fg_item.stock_uom,
			"rate": scrap_rate,
			"is_process_loss": is_process_loss,
		},
	)
	bom_doc.currency = "INR"
	return bom_doc


def create_process_loss_bom_items():
	item_list = [
		("_Test Item - Non Whole UOM", "Kg"),
		("_Test Item - Whole UOM", "Unit"),
		("_Test PL BOM Item", "Unit"),
	]
	return [create_process_loss_bom_item(it) for it in item_list]


def create_process_loss_bom_item(item_tuple):
	item_code, stock_uom = item_tuple
	if frappe.db.exists("Item", item_code) is None:
		return make_item(item_code, {"stock_uom": stock_uom, "valuation_rate": 100})
	else:
		return frappe.get_doc("Item", item_code)
