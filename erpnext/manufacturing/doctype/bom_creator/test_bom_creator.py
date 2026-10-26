# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe

from erpnext.manufacturing.doctype.bom_creator.bom_csv_file import read_bom_csv_file
from erpnext.manufacturing.doctype.bom_creator.item_matcher import ItemMatcher
from erpnext.manufacturing.doctype.bom_creator.step_file import read_step_file
from erpnext.manufacturing.doctype.routing.test_routing import create_routing
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

BICYCLE_PRODUCTS = {
	"BIKE-100": "Bicycle",
	"FRAME-ASM": "Frame Assembly",
	"TUBE-25": "Frame Tube \\X2\\00D8\\X0\\25",
	"BOLT-M6": "Bolt M6",
	"WHEEL-26": "Wheel",
}
BICYCLE_LINKS = [
	("BIKE-100", "FRAME-ASM", 1),
	("FRAME-ASM", "TUBE-25", 3),
	("FRAME-ASM", "BOLT-M6", 4),
	("BIKE-100", "WHEEL-26", 2),
	("BIKE-100", "BOLT-M6", 2),
]


class TestBOMCreator(ERPNextTestSuite):
	def test_step_file_gives_assembly_tree_with_quantities(self):
		design = read_step_file(make_step_content(BICYCLE_PRODUCTS, BICYCLE_LINKS))

		self.assertEqual(design["design_name"], "Bicycle")
		frame, wheel, bolt = design["parts"]
		self.assertEqual((frame["part_number"], frame["quantity"]), ("FRAME-ASM", 1))
		self.assertEqual((wheel["part_number"], wheel["quantity"]), ("WHEEL-26", 2))
		self.assertEqual((bolt["part_number"], bolt["quantity"]), ("BOLT-M6", 2))
		self.assertEqual(
			[(part["part_name"], part["quantity"]) for part in frame["children"]],
			[("Frame Tube Ø25", 3), ("Bolt M6", 4)],
		)

	def test_incomplete_step_file_is_rejected_with_a_message(self):
		content = make_step_content(BICYCLE_PRODUCTS, BICYCLE_LINKS)
		cut = content.index("NEXT_ASSEMBLY_USAGE_OCCURRENCE") + len("NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO")

		self.assertRaisesRegex(frappe.ValidationError, "incomplete or damaged", read_step_file, content[:cut])

	def test_step_file_with_a_damaged_reference_is_rejected_with_a_message(self):
		content = make_step_content(BICYCLE_PRODUCTS, BICYCLE_LINKS).replace(
			"'NAUO1001','','',#", "'NAUO1001','','',#X"
		)

		self.assertRaisesRegex(frappe.ValidationError, "incomplete or damaged", read_step_file, content)

	def test_csv_file_with_levels_or_item_numbers_gives_same_tree(self):
		by_level = read_bom_csv_file(
			"Level,Part Number,Part Name,Quantity\n1,FRAME-ASM,Frame Assembly,1\n2,TUBE-25,Frame Tube,3\n1,WHEEL-26,Wheel,2\n"
		)
		by_item_number = read_bom_csv_file(
			"Item Number,Part Number,Part Name,Quantity\n1,FRAME-ASM,Frame Assembly,1\n1.1,TUBE-25,Frame Tube,3\n2,WHEEL-26,Wheel,2\n"
		)

		self.assertEqual(by_level, by_item_number)
		frame, wheel = by_level["parts"]
		self.assertEqual(frame["children"][0]["part_number"], "TUBE-25")
		self.assertEqual(wheel["quantity"], 2)

	def test_csv_file_with_a_blank_level_uses_the_item_number(self):
		design = read_bom_csv_file(
			"Level,Item Number,Part Number,Quantity\n1,1,FRAME-ASM,1\n,1.1,TUBE-25,3\n,2,WHEEL-26,2\n"
		)

		frame, wheel = design["parts"]
		self.assertEqual(frame["children"][0]["part_number"], "TUBE-25")
		self.assertEqual(wheel["part_number"], "WHEEL-26")

	def test_csv_file_needs_a_quantity_column(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "Quantity column", read_bom_csv_file, "Level,Part Number\n1,FRAME-ASM\n"
		)

		design = read_bom_csv_file("Level,Part Number,Qty\n1,FRAME-ASM,4\n")
		self.assertEqual(design["parts"][0]["quantity"], 4)

	def test_csv_file_with_level_gap_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			read_bom_csv_file,
			"Level,Part Number,Quantity\n1,FRAME-ASM,1\n3,TUBE-25,3\n",
		)

	def test_importing_step_file_creates_parts_linked_to_their_assembly(self):
		design = make_design()

		self.assertEqual(design.design_name, "Bicycle")
		parts = {row.part_number: row for row in design.items if row.parent_node_id == 0}
		self.assertEqual(list(parts), ["FRAME-ASM", "WHEEL-26", "BOLT-M6"])
		self.assertTrue(parts["FRAME-ASM"].is_expandable)
		self.assertFalse(parts["WHEEL-26"].is_expandable)

		frame_parts = [row for row in design.items if row.parent_node_id == parts["FRAME-ASM"].node_id]
		self.assertEqual(
			[(row.part_number, row.qty) for row in frame_parts], [("TUBE-25", 3), ("BOLT-M6", 4)]
		)
		self.assertTrue(all(row.source == "CAD File" and row.do_not_explode for row in design.items))

	def test_design_without_file_is_built_by_hand(self):
		for item_code in (
			"_Test Creator Hand Product",
			"_Test Creator Hand Assembly",
			"_Test Creator Hand Part",
		):
			make_item(item_code, {"is_stock_item": 1})

		design = make_bom_creator(
			item_code="_Test Creator Hand Product",
			items=[
				{"node_id": 1, "item_code": "_Test Creator Hand Assembly", "qty": 2},
				{"node_id": 2, "parent_node_id": 1, "item_code": "_Test Creator Hand Part", "qty": 3},
			],
		)
		self.assertEqual(design.design_name, "_Test Creator Hand Product")
		self.assertEqual(design.items[0].part_number, "_Test Creator Hand Assembly")
		design.submit()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["_Test Creator Hand Assembly"]), {"_Test Creator Hand Part": 3})
		self.assertEqual(
			get_bom_items(boms["_Test Creator Hand Product"]), {"_Test Creator Hand Assembly": 2}
		)

	def test_part_tree_makes_a_bom_for_every_assembly(self):
		design = make_mapped_design()
		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 3, "BOLT-M6": 4})
		finished_good_bom = frappe.get_doc("BOM", boms["BIKE-100"])
		self.assertEqual(
			[(row.item_code, row.qty, row.bom_no) for row in finished_good_bom.items],
			[("FRAME-ASM", 1, boms["FRAME-ASM"]), ("WHEEL-26", 2, ""), ("BOLT-M6", 2, "")],
		)
		self.assertEqual(finished_good_bom.with_operations, 0)
		self.assertEqual(design.status, "Completed")

	def test_finished_good_bom_is_made_for_the_finished_good_quantity(self):
		design = make_mapped_design()
		design.qty = 2
		design.save()

		boms = make_boms(design)

		self.assertEqual(frappe.db.get_value("BOM", boms["BIKE-100"], "quantity"), 2)
		self.assertEqual(get_bom_items(boms["BIKE-100"]), {"FRAME-ASM": 2, "WHEEL-26": 4, "BOLT-M6": 4})
		self.assertEqual(frappe.db.get_value("BOM", boms["FRAME-ASM"], "quantity"), 1)
		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 3, "BOLT-M6": 4})

	def test_part_tree_uses_edited_quantity_and_added_material(self):
		make_item("PAINT-RED", {"is_stock_item": 1, "stock_uom": "Litre"})
		design = make_mapped_design()
		get_part(design, "TUBE-25").qty = 5
		design.append(
			"items",
			{"item_code": "PAINT-RED", "qty": 0.5, "parent_node_id": get_part(design, "FRAME-ASM").node_id},
		)
		design.save()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 5, "BOLT-M6": 4, "PAINT-RED": 0.5})

	def test_part_tree_leaves_out_excluded_parts_and_their_branch(self):
		design = make_mapped_design()
		get_part(design, "WHEEL-26").exclude_from_bom = 1
		get_part(design, "BOLT-M6", parent="FRAME-ASM").exclude_from_bom = 1
		get_part(design, "TUBE-25").item_code = None
		design.save()

		get_part(design, "FRAME-ASM").exclude_from_bom = 1
		design.save()
		boms = make_boms(design)

		self.assertEqual(list(boms), ["BIKE-100"])
		self.assertEqual(get_bom_items(boms["BIKE-100"]), {"BOLT-M6": 2})

	def test_part_tree_adds_quantities_of_parts_mapped_to_one_item(self):
		design = make_mapped_design()
		get_part(design, "WHEEL-26").item_code = "BOLT-M6"
		design.save()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["BIKE-100"]), {"FRAME-ASM": 1, "BOLT-M6": 4})

	def test_unmapped_parts_are_not_reported_as_mapped_to_one_item(self):
		design = make_mapped_design()
		get_part(design, "FRAME-ASM").item_code = None
		get_part(design, "WHEEL-26").item_code = None

		problems = design.get_bom_plan().get_problems()

		self.assertFalse([problem for problem in problems if "in the same assembly" in problem])

	def test_operation_plan_refuses_two_boms_for_one_item(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		get_part(design, "WHEEL-26").item_code = "FRAME-ASM"
		for part_number in ("FRAME-ASM", "WHEEL-26"):
			add_operation(design, "_Test Creator Welding", bom_node_id=get_part(design, part_number).node_id)

		problems = design.get_bom_plan().get_problems()

		self.assertTrue([problem for problem in problems if "Only one BOM can be made" in problem])

	def test_assemblies_of_one_item_need_the_same_raw_materials(self):
		design = make_mapped_design()
		wheel = get_part(design, "WHEEL-26")
		wheel.item_code = "FRAME-ASM"
		design.append("items", {"item_code": "TUBE-25", "qty": 1, "parent_node_id": wheel.node_id})
		design.save()

		self.assertRaisesRegex(frappe.ValidationError, "different raw materials", design.enqueue_create_boms)

	def test_part_mapped_to_its_own_assembly_is_refused(self):
		design = make_mapped_design()
		get_part(design, "TUBE-25").item_code = "FRAME-ASM"
		design.save()

		self.assertRaisesRegex(frappe.ValidationError, "its own assembly", design.enqueue_create_boms)

	def test_each_operation_makes_an_item_that_the_next_operation_uses(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		welded_frame = make_item("_Test Creator Welded Frame", {"is_stock_item": 1}).name
		welding = add_operation(design, "_Test Creator Welding", output_item=welded_frame)
		assembly = add_operation(design, "_Test Creator Assembly")
		add_material(design, part="TUBE-25", qty=3, operation=welding)
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "qty": 1})
		add_material(design, part="WHEEL-26", qty=2, operation=assembly)
		design.save()

		bom = frappe.get_doc("BOM", make_boms(design)["BIKE-100"])

		self.assertEqual(bom.track_semi_finished_goods, 1)
		self.assertEqual(
			[(row.finished_good, row.is_final_finished_good) for row in bom.operations],
			[(welded_frame, 0), ("BIKE-100", 1)],
		)
		self.assertEqual(
			[(row.item_code, row.operation_row_id) for row in bom.items],
			[("TUBE-25", 1), (welded_frame, 2), ("WHEEL-26", 2)],
		)

	def test_operation_output_quantity_is_for_one_finished_good(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		design.qty = 3
		welded_frame = make_item("_Test Creator Welded Frame", {"is_stock_item": 1}).name
		welding = add_operation(design, "_Test Creator Welding", output_item=welded_frame, output_quantity=2)
		assembly = add_operation(design, "_Test Creator Assembly")
		add_material(design, part="TUBE-25", qty=3, operation=welding)
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "qty": 2})
		design.save()

		bom = frappe.get_doc("BOM", make_boms(design)["BIKE-100"])

		self.assertEqual([row.finished_good_qty for row in bom.operations], [6, 3])

	def test_output_of_an_earlier_operation_is_not_exploded(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		design = make_mapped_design(produce_item_at_each_operation=True)
		welded_frame = make_item("_Test Creator Welded Frame", {"is_stock_item": 1}).name
		make_bom(item=welded_frame, raw_materials=["_Test Item"], currency="INR")
		welding = add_operation(design, "_Test Creator Welding", output_item=welded_frame)
		assembly = add_operation(design, "_Test Creator Assembly")
		add_material(design, part="TUBE-25", qty=3, operation=welding)
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "qty": 1})
		design.save()

		bom = frappe.get_doc("BOM", make_boms(design)["BIKE-100"])

		row = next(row for row in bom.items if row.item_code == welded_frame)
		self.assertEqual((row.bom_no, row.do_not_explode), ("", 1))

	def test_sub_assembly_gets_its_own_bom_used_in_the_finished_good_bom(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		frame = get_part(design, "FRAME-ASM").node_id
		add_material(design, part="TUBE-25", qty=3, bom=frame)
		add_material(design, part="BOLT-M6", qty=4, bom=frame)
		add_material(design, part="FRAME-ASM", qty=1)
		add_material(design, part="WHEEL-26", qty=2)
		design.save()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 3, "BOLT-M6": 4})
		finished_good_bom = frappe.get_doc("BOM", boms["BIKE-100"])
		self.assertEqual(
			{row.item_code: row.bom_no for row in finished_good_bom.items},
			{"FRAME-ASM": boms["FRAME-ASM"], "WHEEL-26": ""},
		)
		self.assertEqual(design.status, "Completed")

	def test_item_outside_the_design_gets_its_own_sub_assembly_bom(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		panel = make_item("_Test Creator Printed Panel", {"is_stock_item": 1}).name
		node_id = max(row.node_id for row in design.items) + 1
		design.append(
			"items",
			{
				"node_id": node_id,
				"part_number": panel,
				"part_name": panel,
				"item_code": panel,
				"qty": 1,
				"source": "Manual",
			},
		)
		add_material(design, part="TUBE-25", qty=3, bom=node_id)
		design.append("materials", {"item_code": panel, "qty": 2})
		add_material(design, part="WHEEL-26", qty=2)
		design.save()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms[panel]), {"TUBE-25": 3})
		finished_good_bom = frappe.get_doc("BOM", boms["BIKE-100"])
		self.assertEqual(
			{row.item_code: row.bom_no for row in finished_good_bom.items},
			{panel: boms[panel], "WHEEL-26": ""},
		)

	def test_operation_plan_cost_counts_sub_assembly_materials(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		set_valuation_rates({"TUBE-25": 10, "BOLT-M6": 1, "WHEEL-26": 50})
		frame = get_part(design, "FRAME-ASM").node_id
		add_material(design, part="TUBE-25", qty=3, bom=frame)
		add_material(design, part="BOLT-M6", qty=4, bom=frame)
		add_material(design, part="FRAME-ASM", qty=1)
		add_material(design, part="WHEEL-26", qty=2)
		design.qty = 2
		design.save()

		self.assertEqual(design.raw_material_cost, ((3 * 10 + 4 * 1) + 2 * 50) * 2)

	def test_create_boms_lists_every_problem(self):
		design = make_submitted_design()
		design.track_semi_finished_goods = 1
		operation = add_operation(design, "_Test Creator Welding", workstation_type="")
		add_material(design, part="TUBE-25", qty=3, operation=operation)
		add_material(design, part="BOLT-M6", qty=4, bom=get_part(design, "FRAME-ASM").node_id)
		design.save()

		with self.assertRaises(frappe.ValidationError) as error:
			design.enqueue_create_boms()

		self.assertIn("map an item before creating its BOM", str(error.exception))
		self.assertIn("set the Workstation Type", str(error.exception))
		self.assertIn("map an item for every raw material", str(error.exception))

	def test_material_needs_exactly_one_source(self):
		design = make_design()
		design.append("materials", {"item_code": "_Test Item", "part_node_id": 1, "qty": 1})

		self.assertRaises(frappe.ValidationError, design.save)

	def test_operation_output_is_used_only_when_each_operation_makes_an_item(self):
		design = make_design()
		welding = add_operation(design, "_Test Creator Welding")
		assembly = add_operation(design, "_Test Creator Assembly")
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "qty": 1})

		self.assertRaises(frappe.ValidationError, design.save)

	def test_output_of_a_missing_operation_gives_no_item(self):
		from erpnext.manufacturing.doctype.bom_creator.operation_plan import OperationPlan

		material = frappe._dict(part_node_id=0, bom_node_id=0, from_operation_id=99, item_code=None)

		self.assertIsNone(OperationPlan(make_design()).get_material_item(material))

	def test_new_revision_keeps_edited_quantity_until_the_design_changes_it(self):
		design = make_mapped_design()
		get_part(design, "TUBE-25").qty = 5
		get_part(design, "BOLT-M6", parent="FRAME-ASM").qty = 10
		design.save()

		revision = frappe.get_doc("BOM Creator", design.make_new_revision())
		revision.design_file = make_step_file(
			BICYCLE_PRODUCTS,
			[
				link if link != ("FRAME-ASM", "BOLT-M6", 4) else ("FRAME-ASM", "BOLT-M6", 6)
				for link in BICYCLE_LINKS
			],
		)
		revision.save()

		tube = get_part(revision, "TUBE-25")
		self.assertEqual((tube.qty, tube.design_quantity), (5, 3))
		bolt = get_part(revision, "BOLT-M6", parent="FRAME-ASM")
		self.assertEqual((bolt.qty, bolt.design_quantity, bolt.change_type), (10, 6, "Quantity Changed"))

	def test_create_boms_needs_submitted_design(self):
		design = make_design()

		self.assertRaises(frappe.ValidationError, design.enqueue_create_boms)

	def test_part_model_must_be_a_supported_3d_file(self):
		for model_file, is_valid in (("/files/handle.pdf", False), ("/files/handle.glb", True)):
			design = make_design()
			design.append(
				"items",
				{
					"item_code": "_Test Item",
					"qty": 1,
					"model_file": model_file,
					"placements": '[{"position": [0, 10, 0], "quaternion": [0, 0, 0, 1]}]',
				},
			)

			if is_valid:
				design.save()
			else:
				self.assertRaises(frappe.ValidationError, design.save)

	def test_create_items_makes_items_only_for_parts_used_in_boms(self):
		design = make_submitted_design()
		design.track_semi_finished_goods = 1
		add_material(design, part="TUBE-25", qty=3)
		design.save()
		design.create_items(item_group="_Test Item Group", stock_uom="Nos")

		self.assertEqual(get_part(design, "TUBE-25").item_code, "TUBE-25")
		self.assertFalse(get_part(design, "WHEEL-26").item_code)

	def test_parts_from_submitted_design_file_cannot_be_removed(self):
		design = make_submitted_design()
		design.items = [row for row in design.items if row.part_number != "WHEEL-26"]

		self.assertRaises(frappe.ValidationError, design.save)

	def test_new_revision_keeps_mapping_materials_and_shows_changes(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		add_material(design, part="TUBE-25", qty=3, bom=get_part(design, "FRAME-ASM").node_id)
		add_material(design, part="WHEEL-26", qty=2)
		design.save()

		revision = frappe.get_doc("BOM Creator", design.make_new_revision())
		revision.design_file = make_step_file(
			{**BICYCLE_PRODUCTS, "BELL-01": "Bell"},
			[
				("BIKE-100", "BELL-01", 1),
				("BIKE-100", "FRAME-ASM", 1),
				("FRAME-ASM", "TUBE-25", 3),
				("FRAME-ASM", "BOLT-M6", 6),
				("BIKE-100", "BOLT-M6", 2),
			],
		)
		revision.save()

		self.assertEqual(revision.revision, 2)
		self.assertEqual(get_part(revision, "FRAME-ASM").item_code, "FRAME-ASM")
		self.assertEqual(get_part(revision, "BELL-01").change_type, "Added")
		self.assertEqual(get_part(revision, "BOLT-M6", parent="FRAME-ASM").change_type, "Quantity Changed")
		self.assertEqual(
			[(row.bom_node_id, row.part_node_id) for row in revision.materials],
			[(get_part(revision, "FRAME-ASM").node_id, get_part(revision, "TUBE-25").node_id)],
		)

		changes = revision.get_revision_changes()
		self.assertEqual([row["part_number"] for row in changes["added"]], ["BELL-01"])
		self.assertEqual([row["part_number"] for row in changes["removed"]], ["WHEEL-26"])
		self.assertEqual(
			[(row["path"], row["previous_quantity"], row["quantity"]) for row in changes["quantity_changed"]],
			[("FRAME-ASM > BOLT-M6", 4, 6)],
		)

		revision.submit()
		design.reload()
		self.assertEqual(design.status, "Superseded")
		self.assertRaises(frappe.ValidationError, design.make_new_revision)

	def test_assembly_cost_is_the_cost_of_its_raw_materials(self):
		design = make_mapped_design()
		set_valuation_rates({"TUBE-25": 10, "BOLT-M6": 1, "WHEEL-26": 50})
		design.qty = 2
		design.save()

		frame = get_part(design, "FRAME-ASM")
		self.assertEqual((frame.rate, frame.amount), (34, 34))
		self.assertEqual(get_part(design, "WHEEL-26").amount, 100)
		self.assertEqual(design.raw_material_cost, (34 + 100 + 2) * 2)

	def test_part_using_an_existing_bom_costs_the_bom(self):
		design = make_mapped_design()
		set_valuation_rates({"TUBE-25": 10})
		frame_bom = make_test_bom("FRAME-ASM", 2, {"TUBE-25": 6})
		frame = get_part(design, "FRAME-ASM")
		for row in design.items:
			if row.parent_node_id == frame.node_id:
				row.exclude_from_bom = 1

		frame.update({"bom_no": frame_bom, "do_not_explode": 0})
		design.save()

		self.assertEqual(get_part(design, "FRAME-ASM").rate, 30)

	def test_rates_are_converted_to_the_creator_currency(self):
		make_item("_Test Creator USD Material", {"valuation_rate": 800})
		design = make_bom_creator(
			currency="USD",
			conversion_rate=80,
			items=[{"item_code": "_Test Creator USD Material", "qty": 1}],
		)

		self.assertEqual(design.items[0].rate, 10)
		self.assertEqual(design.raw_material_cost, 10)

	def test_currency_change_refreshes_the_exchange_rate(self):
		if not frappe.db.exists("Currency", "TSR"):
			frappe.get_doc({"doctype": "Currency", "currency_name": "TSR", "enabled": 1}).insert()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": frappe.utils.today(),
				"from_currency": "TSR",
				"to_currency": "INR",
				"exchange_rate": 50,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()

		design = make_bom_creator(currency="USD", conversion_rate=80)
		design.currency = "TSR"
		design.save()

		self.assertEqual(design.conversion_rate, 50)

	def test_rate_is_taken_from_the_default_warehouse(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		material = make_item("_Test Creator Warehouse Material", {"is_stock_item": 1}).name
		make_stock_entry(item_code=material, target="Stores - _TC", qty=10, basic_rate=100)
		make_stock_entry(item_code=material, target="Finished Goods - _TC", qty=10, basic_rate=300)

		design = make_bom_creator(
			set_rate_based_on_warehouse=1,
			default_warehouse="Stores - _TC",
			items=[{"item_code": material, "qty": 1}],
		)

		self.assertEqual(design.items[0].rate, 100)

	def test_default_source_warehouse_is_set_on_the_boms(self):
		design = make_bom_creator(
			default_warehouse="Stores - _TC", items=[{"item_code": "_Test Item", "qty": 1}]
		)
		design.submit()

		bom = make_boms(design)[design.item_code]

		self.assertEqual(frappe.db.get_value("BOM", bom, "default_source_warehouse"), "Stores - _TC")

	def test_items_from_a_bom_come_as_a_tree_for_one_unit(self):
		from erpnext.manufacturing.doctype.bom_creator.bom_creator import get_bom_tree

		kit_bom, hinge_bom = make_kit_bom()
		self.assertEqual(
			[(row["item_code"], row["qty"], row["bom_no"], row["children"]) for row in get_bom_tree(kit_bom)],
			[("_Test Creator Hinge", 1, hinge_bom, []), ("_Test Creator Plate", 3, "", [])],
		)
		hinge = get_bom_tree(kit_bom, include_sub_assemblies=True)[0]
		self.assertEqual((hinge["bom_no"], hinge["do_not_explode"]), ("", 1))
		self.assertEqual(
			[(row["item_code"], row["qty"]) for row in hinge["children"]], [("_Test Creator Pin", 2)]
		)

	def test_items_of_a_sub_assembly_bom_need_read_permission_on_it(self):
		from erpnext.manufacturing.doctype.bom_creator.bom_creator import get_bom_tree

		kit_bom, hinge_bom = make_kit_bom()

		def has_permission(doctype, ptype, doc, throw):
			if doc == hinge_bom:
				raise frappe.PermissionError

		with patch.object(frappe, "has_permission", side_effect=has_permission):
			self.assertEqual(len(get_bom_tree(kit_bom)), 2)
			self.assertRaises(frappe.PermissionError, get_bom_tree, kit_bom, include_sub_assemblies=True)

	def test_unit_of_measure_sets_stock_quantity_and_amount(self):
		material = make_item(
			"_Test Creator Box Material",
			{
				"valuation_rate": 10,
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			},
		).name
		design = make_bom_creator(items=[{"item_code": material, "qty": 3, "uom": "Box"}])

		row = design.items[0]
		self.assertEqual((row.conversion_factor, row.stock_qty, row.amount), (12, 36, 360))

	def test_changed_unit_of_measure_gets_its_own_conversion_factor(self):
		material = make_item(
			"_Test Creator Box Material",
			{
				"valuation_rate": 10,
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			},
		).name
		design = make_bom_creator(items=[{"item_code": material, "qty": 3, "uom": "Box"}])
		design.items[0].uom = "Nos"
		design.save()

		row = design.items[0]
		self.assertEqual((row.conversion_factor, row.stock_qty), (1, 3))

	def test_stock_unit_without_a_conversion_row_gets_factor_one(self):
		material = make_item(
			"_Test Creator Box Material",
			{
				"valuation_rate": 10,
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			},
		).name
		design = make_bom_creator(items=[{"item_code": material, "qty": 3, "uom": "Box"}])
		frappe.db.delete("UOM Conversion Detail", {"parent": material, "uom": "Nos"})
		design.items[0].uom = "Nos"
		design.save()

		row = design.items[0]
		self.assertEqual((row.conversion_factor, row.stock_qty), (1, 3))

	def test_parts_of_one_item_in_different_units_stay_separate_bom_rows(self):
		material = make_item(
			"_Test Creator Box Material",
			{
				"valuation_rate": 10,
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			},
		).name
		design = make_bom_creator(
			items=[
				{"item_code": material, "qty": 1, "uom": "Box"},
				{"item_code": material, "qty": 2, "uom": "Nos"},
			]
		)
		design.submit()
		boms = make_boms(design)

		self.assertEqual(
			sorted(
				(row.uom, row.qty, row.stock_qty)
				for row in frappe.get_doc("BOM", boms[design.item_code]).items
			),
			[("Box", 1, 12), ("Nos", 2, 2)],
		)

	def test_raw_material_keeps_its_own_bom(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		make_item("_Test Creator Pedal", {"is_stock_item": 1})
		pedal_bom = make_bom(item="_Test Creator Pedal", raw_materials=["_Test Item"], currency="INR")
		design = make_bom_creator(
			items=[
				{"item_code": "_Test Creator Pedal", "qty": 1, "do_not_explode": 0, "bom_no": pedal_bom.name}
			]
		)
		design.submit()

		boms = make_boms(design)

		row = frappe.db.get_value(
			"BOM Item",
			{"parent": boms[design.item_code], "item_code": "_Test Creator Pedal"},
			["bom_no", "do_not_explode"],
			as_dict=True,
		)
		self.assertEqual((row.bom_no, row.do_not_explode), (pedal_bom.name, 0))

	def test_assembly_uses_existing_bom_instead_of_a_new_one(self):
		design = make_mapped_design()
		frame_bom = make_test_bom("FRAME-ASM", 1, {"TUBE-25": 2})
		frame = get_part(design, "FRAME-ASM")
		for row in design.items:
			if row.parent_node_id == frame.node_id:
				row.exclude_from_bom = 1

		frame.update({"bom_no": frame_bom, "do_not_explode": 0})
		design.save()

		boms = make_boms(design)

		self.assertEqual(list(boms), ["BIKE-100"])
		self.assertEqual(
			frappe.db.get_value("BOM Item", {"parent": boms["BIKE-100"], "item_code": "FRAME-ASM"}, "bom_no"),
			frame_bom,
		)

	def test_existing_bom_must_belong_to_the_part_item(self):
		design = make_mapped_design()
		wheel_bom = make_test_bom("WHEEL-26", 1, {"BOLT-M6": 1})
		get_part(design, "FRAME-ASM").update({"bom_no": wheel_bom, "do_not_explode": 0})

		self.assertRaisesRegex(frappe.ValidationError, "is not an active, submitted BOM", design.save)

	def test_phantom_finished_good_must_be_a_non_stock_item(self):
		self.assertRaisesRegex(frappe.ValidationError, "Phantom BOM cannot", make_bom_creator, is_phantom=1)

		item_code = make_item("_Test Creator Phantom Kit", {"is_stock_item": 0}).name
		design = make_bom_creator(
			item_code=item_code, is_phantom=1, items=[{"item_code": "_Test Item", "qty": 1}]
		)
		design.submit()

		boms = make_boms(design)

		self.assertEqual(frappe.db.get_value("BOM", boms[item_code], "is_phantom_bom"), 1)

	def test_finished_good_changed_after_submit_must_match_phantom_setting(self):
		design = make_submitted_design()
		design.item_code = make_item("_Test Creator Service Kit", {"is_stock_item": 0}).name

		self.assertRaisesRegex(frappe.ValidationError, "Non-phantom BOM", design.save)

	def test_submit_rejects_item_operation_without_routing(self):
		design = make_bom_creator(
			items=[{"item_code": "_Test Item", "qty": 1, "operation": "_Test Operation 1"}]
		)

		self.assertRaisesRegex(frappe.ValidationError, "Set a Routing", design.submit)

	def test_finished_good_bom_gets_the_operations_of_the_routing(self):
		routing = create_routing(
			routing_name="_Test Creator Routing",
			operations=[
				{"operation": "_Test Operation 1", "workstation": "_Test Workstation 1", "time_in_mins": 10}
			],
		)
		design = make_bom_creator(
			routing=routing.name,
			items=[{"item_code": "_Test Item", "qty": 1, "operation": "_Test Operation 1"}],
		)
		design.submit()

		bom = frappe.get_doc("BOM", make_boms(design)[design.item_code])

		self.assertEqual((bom.with_operations, bom.routing), (1, routing.name))
		self.assertEqual([row.operation for row in bom.operations], ["_Test Operation 1"])
		self.assertEqual(bom.items[0].operation, "_Test Operation 1")

	def test_boms_are_created_in_the_background_from_the_saved_creator(self):
		from frappe.handler import run_doc_method

		design = make_mapped_design()
		posted = design.as_dict()
		posted["qty"] = 7
		frappe.local.request = frappe._dict(method="POST")
		self.addCleanup(delattr, frappe.local, "request")

		with patch.object(frappe, "enqueue_doc") as enqueue_doc:
			frappe.local.response = frappe._dict(docs=[])
			run_doc_method("enqueue_create_boms", docs=json.dumps(posted, default=str))

		self.assertEqual(enqueue_doc.call_args.args, ("BOM Creator", design.name, "create_boms"))
		self.assertEqual(
			frappe.db.get_value("BOM Creator", design.name, ["status", "qty"]), ("In Progress", 1)
		)

	def test_failed_run_keeps_the_error_and_a_later_run_clears_it(self):
		from erpnext.manufacturing.doctype.bom_creator.part_tree_plan import PartTreePlan

		design = make_mapped_design()
		failure = frappe.ValidationError("Item TUBE-25 is disabled")
		with (
			patch.object(PartTreePlan, "make_boms", side_effect=failure),
			patch.object(frappe.db, "rollback"),
		):
			design.create_boms()

		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Failed")
		self.assertIn(
			"Item TUBE-25 is disabled", frappe.db.get_value("BOM Creator", design.name, "error_log")
		)

		design.reload()
		design.create_boms()
		self.assertEqual(
			frappe.db.get_value("BOM Creator", design.name, ["status", "error_log"]), ("Completed", None)
		)

	def test_finished_run_does_not_stay_in_progress(self):
		from erpnext.manufacturing.doctype.bom_creator.part_tree_plan import PartTreePlan

		design = make_mapped_design()
		with patch.object(PartTreePlan, "make_boms"), patch.object(
			PartTreePlan, "has_all_boms", return_value=False
		):
			design.create_boms()

		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Submitted")

	def test_saving_a_submitted_design_refreshes_its_status(self):
		from erpnext.manufacturing.doctype.bom_creator.part_tree_plan import PartTreePlan

		design = make_mapped_design()
		make_boms(design)
		self.assertEqual(design.status, "Completed")

		with patch.object(PartTreePlan, "has_all_boms", return_value=False):
			design.save()

		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Submitted")

	def test_create_boms_needs_permission_to_submit_boms(self):
		design = make_mapped_design()

		def has_permission(doctype, *args, **kwargs):
			if doctype == "BOM":
				raise frappe.PermissionError
			return True

		with patch.object(frappe, "has_permission", side_effect=has_permission):
			self.assertRaises(frappe.PermissionError, design.enqueue_create_boms)

	def test_part_added_to_a_submitted_revision_is_marked_added(self):
		design = make_mapped_design()
		revision = frappe.get_doc("BOM Creator", design.make_new_revision())
		revision.submit()
		revision.append(
			"items",
			{"item_code": "_Test Item", "part_name": "_Test Item", "qty": 1, "source": "Manual"},
		)
		revision.save()

		self.assertEqual(revision.items[-1].change_type, "Added")

	def test_cancelling_a_revision_reopens_the_previous_revision(self):
		design = make_mapped_design()
		revision = frappe.get_doc("BOM Creator", design.make_new_revision())
		revision.submit()
		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Superseded")

		revision.cancel()

		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Submitted")

	def test_revision_changes_need_read_permission_on_the_previous_revision(self):
		design = make_mapped_design()
		revision = frappe.get_doc("BOM Creator", design.make_new_revision())

		def has_permission(doctype, ptype=None, doc=None, **kwargs):
			if doc == design.name:
				raise frappe.PermissionError
			return True

		with patch.object(frappe, "has_permission", side_effect=has_permission):
			self.assertRaises(frappe.PermissionError, revision.get_revision_changes)

	def test_cancelling_the_top_bom_reopens_the_creator_and_keeps_sub_assembly_boms(self):
		design = make_mapped_design()
		boms = make_boms(design)

		frappe.get_doc("BOM", boms["BIKE-100"]).cancel()
		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Submitted")

		design.reload()
		new_boms = make_boms(design)
		self.assertEqual(new_boms["FRAME-ASM"], boms["FRAME-ASM"])
		self.assertNotEqual(new_boms["BIKE-100"], boms["BIKE-100"])
		self.assertEqual(design.status, "Completed")

	def test_new_design_file_keeps_the_mapping_of_each_repeated_part(self):
		bolts = [
			make_item(code, {"is_stock_item": 1}).name
			for code in ("_Test Creator Bolt A", "_Test Creator Bolt B")
		]
		content = "Level,Part Number,Quantity\n1,FRAME-ASM,1\n2,BOLT-M6,2\n2,BOLT-M6,3\n"
		design = make_bom_creator(design_file=make_csv_file(content))
		for row, item_code in zip(get_parts(design, "BOLT-M6"), bolts, strict=True):
			row.item_code = item_code
		design.save()

		design.design_file = make_csv_file(content + "1,WHEEL-26,2\n")
		design.save()

		self.assertEqual(
			[(row.item_code, row.qty) for row in get_parts(design, "BOLT-M6")], [(bolts[0], 2), (bolts[1], 3)]
		)

	def test_parts_check_on_update_after_submit_needs_no_previous_version(self):
		design = frappe.get_doc("BOM Creator", make_submitted_design().name)

		design.validate_cad_parts_unchanged()

	def test_cancelled_design_gets_status_cancelled(self):
		design = make_submitted_design()
		design.cancel()

		self.assertEqual(frappe.db.get_value("BOM Creator", design.name, "status"), "Cancelled")

	def test_create_boms_waits_for_a_running_job_and_retries_a_stuck_one(self):
		design = make_mapped_design()
		design.db_set("status", "In Progress")
		job_check = "erpnext.manufacturing.doctype.bom_creator.bom_creator.is_job_enqueued"

		with patch(job_check, return_value=True):
			self.assertRaisesRegex(frappe.ValidationError, "being created", design.enqueue_create_boms)

		with patch(job_check, return_value=False), patch.object(frappe, "enqueue_doc") as enqueue_doc:
			design.enqueue_create_boms()

		self.assertEqual(enqueue_doc.call_args.kwargs["job_id"], design.create_boms_job_id)

	def test_migration_finds_old_designs_that_have_a_naming_series(self):
		from erpnext.patches.v16_0.move_bom_creator_items_to_part_tree import get_creators

		design = make_design()
		self.assertEqual(design.naming_series, "BOM-CRE-.YYYY.-")
		self.assertEqual([creator.name for creator in get_creators([design.name])], [design.name])

	def test_migration_finds_old_designs_without_rows(self):
		from erpnext.patches.v16_0.move_bom_creator_items_to_part_tree import get_creators

		design = make_bom_creator()
		design.db_set("design_name", None)
		self.assertIn(design.name, [creator.name for creator in get_creators([])])

	def test_migrated_tree_marks_assemblies_as_expandable(self):
		from erpnext.patches.v16_0.move_bom_creator_items_to_part_tree import get_item_updates

		rows = [
			frappe._dict(name="frame", fg_reference_id="BOM-CRE-OLD", item_code="FRAME-ASM", qty=2),
			frappe._dict(
				name="tube", fg_reference_id="frame", item_code="TUBE-25", qty=6, rate=5, base_rate=10
			),
		]
		updates = get_item_updates(frappe._dict(name="BOM-CRE-OLD", qty=2), rows)

		self.assertEqual((updates["frame"]["is_expandable"], updates["tube"]["is_expandable"]), (1, 0))
		self.assertEqual([updates["tube"][field] for field in ("qty", "amount", "base_amount")], [3, 15, 30])

	def test_item_matcher_maps_a_part_number_written_without_punctuation(self):
		make_item("ZPH100", {"item_name": "Zephyr Plate"})
		make_item("_Test Zephyr Other Plate", {"item_name": "Plate"})

		self.assertEqual(
			get_item_match(part_number="ZPH-100", part_name="Plate"),
			{"item_code": "ZPH100", "score": 100, "matched_on": "Item Code", "is_selected": True},
		)

	def test_item_matcher_ticks_an_item_name_with_the_words_in_another_order(self):
		item = make_item("_Test Zephyr Bracket", {"item_name": "Bracket Zephyr Steel 2 mm"}).name
		match = get_item_match(part_number="ZB-77", part_name="Zephyr Steel Bracket 2mm")

		self.assertEqual(
			(match["item_code"], match["matched_on"], match["is_selected"]), (item, "Item Name", True)
		)

	def test_item_matcher_does_not_tick_an_item_with_other_numbers(self):
		make_item("ZEPHYR-SEAT-POST-30")
		match = get_item_match(part_number="ZEPHYRSEATPOST31", part_name="Seat Post")

		self.assertEqual((match["item_code"], match["is_selected"]), ("ZEPHYR-SEAT-POST-30", False))
		self.assertLess(match["score"], 90)

	def test_item_matcher_ticks_a_number_written_with_a_leading_zero(self):
		make_item("ZEPHYR-SEAT-LUG-01")
		match = get_item_match(part_number="ZEPHYRSEATLUG1", part_name="Seat Lug")

		self.assertEqual((match["item_code"], match["is_selected"]), ("ZEPHYR-SEAT-LUG-01", True))

	def test_item_matcher_does_not_tick_one_of_two_equal_matches(self):
		for item_code in ("_Test Zephyr Clamp A", "_Test Zephyr Clamp B"):
			make_item(item_code, {"item_name": "Zephyr Saddle Clamp"})
		match = get_item_match(part_number="ZSC-1", part_name="Zephyr Saddle Clamp")

		self.assertEqual((match["score"], match["is_selected"]), (100, False))

	def test_item_matcher_suggests_a_description_match_without_ticking_it(self):
		item = make_item(
			"_Test Zephyr Lever",
			{"item_name": "Zephyr Lever", "description": "<p>Zephyr brake lever for the left hand</p>"},
		).name
		match = get_item_match(part_number="ZBL-9", part_name="Zephyr Brake Lever")

		self.assertEqual(
			(match["item_code"], match["matched_on"], match["is_selected"]), (item, "Description", False)
		)

	def test_item_matcher_reuses_the_item_of_the_part_in_an_earlier_design(self):
		design = make_design()
		item = make_item("_Test Zephyr Tube", {"is_stock_item": 1}).name
		get_part(design, "TUBE-25").item_code = item
		design.save()

		self.assertEqual(
			get_item_match(part_number="TUBE-25", part_name="Frame Tube"),
			{"item_code": item, "score": 100, "matched_on": "Earlier Design", "is_selected": True},
		)

	def test_item_matcher_skips_a_part_without_a_close_item(self):
		self.assertIsNone(get_item_match(part_number="QX-0", part_name="Qwyzzle Gnarf"))

	def test_suggested_items_skip_mapped_and_excluded_parts(self):
		design = make_design()
		for part_number in ("FRAME-ASM", "TUBE-25", "BOLT-M6", "WHEEL-26"):
			make_item(part_number, {"is_stock_item": 1})
		get_part(design, "FRAME-ASM").item_code = "FRAME-ASM"
		get_part(design, "WHEEL-26").exclude_from_bom = 1
		design.save()

		suggested_rows = set(design.get_suggested_items())
		self.assertEqual(
			sorted(row.part_number for row in design.items if row.name in suggested_rows),
			["BOLT-M6", "BOLT-M6", "TUBE-25"],
		)


def make_step_content(products: dict, links: list) -> str:
	entities = ["#1=APPLICATION_CONTEXT('automotive design');", "#2=PRODUCT_CONTEXT('',#1,'mechanical');"]
	definitions = {}
	for index, (part_number, part_name) in enumerate(products.items()):
		entity_id = 10 * (index + 1)
		entities += [
			f"#{entity_id}=PRODUCT('{part_number}','{part_name}','',(#2));",
			f"#{entity_id + 1}=PRODUCT_DEFINITION_FORMATION('','',#{entity_id});",
			f"#{entity_id + 2}=PRODUCT_DEFINITION('design','',#{entity_id + 1},#1);",
		]
		definitions[part_number] = entity_id + 2

	entity_id = 1000
	for parent, child, quantity in links:
		for _index in range(quantity):
			entity_id += 1
			entities.append(
				f"#{entity_id}=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO{entity_id}','','',"
				f"#{definitions[parent]},#{definitions[child]},$);"
			)

	return "ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n" + "\n".join(entities) + "\nENDSEC;\nEND-ISO-10303-21;\n"


def make_step_file(products: dict, links: list) -> str:
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{frappe.generate_hash(length=8)}.step",
			"content": make_step_content(products, links),
			"is_private": 1,
		}
	).insert()
	return file.file_url


def make_csv_file(content: str) -> str:
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{frappe.generate_hash(length=8)}.csv",
			"content": content,
			"is_private": 1,
		}
	).insert()
	return file.file_url


def make_kit_bom() -> tuple[str, str]:
	for item_code in ("_Test Creator Kit", "_Test Creator Hinge", "_Test Creator Pin", "_Test Creator Plate"):
		make_item(item_code, {"is_stock_item": 1, "valuation_rate": 10})

	hinge_bom = make_test_bom("_Test Creator Hinge", 2, {"_Test Creator Pin": 4})
	kit_bom = make_test_bom(
		"_Test Creator Kit",
		1,
		{"_Test Creator Hinge": 1, "_Test Creator Plate": 3},
		{"_Test Creator Hinge": hinge_bom},
	)
	return kit_bom, hinge_bom


def make_bom_creator(**values):
	item_code = values.pop("item_code", None) or make_item("_Test Creator Product", {"is_stock_item": 1}).name
	return frappe.get_doc(
		{"doctype": "BOM Creator", "company": "_Test Company", "item_code": item_code, **values}
	).insert()


def make_design():
	return frappe.get_doc(
		{
			"doctype": "BOM Creator",
			"company": "_Test Company",
			"item_code": make_item("BIKE-100", {"is_stock_item": 1}).name,
			"design_file": make_step_file(BICYCLE_PRODUCTS, BICYCLE_LINKS),
		}
	).insert()


def make_submitted_design():
	design = make_design()
	design.submit()
	return design


def make_mapped_design(produce_item_at_each_operation: bool = False):
	design = make_submitted_design()
	design.track_semi_finished_goods = 1 if produce_item_at_each_operation else 0
	for part in design.items:
		part.item_code = make_item(part.part_number, {"is_stock_item": 1}).name

	design.save()
	return design


def make_test_bom(item_code: str, quantity: float, materials: dict, boms: dict | None = None) -> str:
	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": item_code,
			"company": "_Test Company",
			"currency": "INR",
			"quantity": quantity,
			"items": [
				{"item_code": code, "qty": qty, "bom_no": (boms or {}).get(code, "")}
				for code, qty in materials.items()
			],
		}
	).insert()
	bom.submit()
	return bom.name


def set_valuation_rates(rates: dict):
	for item_code, rate in rates.items():
		frappe.db.set_value("Item", item_code, "valuation_rate", rate)


def add_operation(design, operation: str, workstation_type: str = "_Test Creator Bench", **values) -> int:
	if workstation_type and not frappe.db.exists("Workstation Type", workstation_type):
		frappe.get_doc({"doctype": "Workstation Type", "workstation_type": workstation_type}).insert()

	if not frappe.db.exists("Operation", operation):
		frappe.get_doc({"doctype": "Operation", "name": operation}).insert()

	operation_id = len(design.operations) + 1
	design.append(
		"operations",
		{
			"operation_id": operation_id,
			"operation": operation,
			"workstation_type": workstation_type,
			"time_in_mins": 30,
			**values,
		},
	)
	return operation_id


def add_material(design, part: str, qty: float, operation: int = 0, bom: int = 0):
	design.append(
		"materials",
		{
			"bom_node_id": bom,
			"operation_id": operation,
			"part_node_id": get_part(design, part).node_id,
			"qty": qty,
		},
	)


def make_boms(design) -> dict:
	design.create_boms()
	design.reload()
	return dict(
		frappe.get_all(
			"BOM",
			filters={"bom_creator": design.name, "docstatus": 1},
			fields=["item", "name"],
			order_by="creation",
			as_list=True,
		)
	)


def get_item_match(**part) -> dict | None:
	return ItemMatcher([frappe._dict(name="part", **part)]).get_matches().get("part")


def get_part(design, part_number: str, parent: str | None = None):
	parent_node_ids = {row.node_id for row in design.items if row.part_number == parent}
	return next(
		row
		for row in design.items
		if row.part_number == part_number and (not parent or row.parent_node_id in parent_node_ids)
	)


def get_parts(design, part_number: str) -> list:
	return [row for row in design.items if row.part_number == part_number]


def get_bom_items(bom: str) -> dict:
	return {row.item_code: row.qty for row in frappe.get_doc("BOM", bom).items}
