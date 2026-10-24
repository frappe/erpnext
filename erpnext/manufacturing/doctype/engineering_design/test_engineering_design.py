# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.engineering_design.bom_csv_file import read_bom_csv_file
from erpnext.manufacturing.doctype.engineering_design.step_file import read_step_file
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


class TestEngineeringDesign(ERPNextTestSuite):
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

	def test_csv_file_with_level_gap_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			read_bom_csv_file,
			"Level,Part Number,Quantity\n1,FRAME-ASM,1\n3,TUBE-25,3\n",
		)

	def test_importing_step_file_creates_parts_linked_to_their_assembly(self):
		design = make_design()

		self.assertEqual(design.design_name, "Bicycle")
		parts = {row.part_number: row for row in design.parts if row.parent_node_id == 0}
		self.assertEqual(list(parts), ["FRAME-ASM", "WHEEL-26", "BOLT-M6"])
		self.assertTrue(parts["FRAME-ASM"].is_assembly)
		self.assertFalse(parts["WHEEL-26"].is_assembly)

		frame_parts = [row for row in design.parts if row.parent_node_id == parts["FRAME-ASM"].node_id]
		self.assertEqual(
			[(row.part_number, row.quantity) for row in frame_parts], [("TUBE-25", 3), ("BOLT-M6", 4)]
		)
		self.assertTrue(all(row.source == "CAD File" for row in design.parts))

	def test_design_without_file_is_built_by_hand(self):
		for item_code in (
			"_Test Design Hand Product",
			"_Test Design Hand Assembly",
			"_Test Design Hand Part",
		):
			make_item(item_code, {"is_stock_item": 1})

		design = frappe.get_doc(
			{
				"doctype": "Engineering Design",
				"company": "_Test Company",
				"design_name": "Hand Made Product",
				"item_code": "_Test Design Hand Product",
				"parts": [
					{
						"node_id": 1,
						"part_number": "_Test Design Hand Assembly",
						"item_code": "_Test Design Hand Assembly",
						"quantity": 2,
					},
					{
						"node_id": 2,
						"parent_node_id": 1,
						"part_number": "_Test Design Hand Part",
						"item_code": "_Test Design Hand Part",
						"quantity": 3,
					},
				],
			}
		).insert()
		design.submit()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["_Test Design Hand Assembly"]), {"_Test Design Hand Part": 3})
		self.assertEqual(get_bom_items(boms["_Test Design Hand Product"]), {"_Test Design Hand Assembly": 2})

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
		design.quantity = 2
		design.save()

		boms = make_boms(design)

		self.assertEqual(frappe.db.get_value("BOM", boms["BIKE-100"], "quantity"), 2)
		self.assertEqual(get_bom_items(boms["BIKE-100"]), {"FRAME-ASM": 2, "WHEEL-26": 4, "BOLT-M6": 4})
		self.assertEqual(frappe.db.get_value("BOM", boms["FRAME-ASM"], "quantity"), 1)
		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 3, "BOLT-M6": 4})

	def test_part_tree_uses_edited_quantity_and_added_material(self):
		make_item("PAINT-RED", {"is_stock_item": 1, "stock_uom": "Litre"})
		design = make_mapped_design()
		get_part(design, "TUBE-25").quantity = 5
		design.append(
			"parts",
			{
				"part_number": "PAINT-RED",
				"item_code": "PAINT-RED",
				"quantity": 0.5,
				"parent_node_id": get_part(design, "FRAME-ASM").node_id,
			},
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

	def test_each_operation_makes_an_item_that_the_next_operation_uses(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		welded_frame = make_item("_Test Design Welded Frame", {"is_stock_item": 1}).name
		welding = add_operation(design, "_Test Design Welding", output_item=welded_frame)
		assembly = add_operation(design, "_Test Design Assembly")
		add_material(design, part="TUBE-25", quantity=3, operation=welding)
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "quantity": 1})
		add_material(design, part="WHEEL-26", quantity=2, operation=assembly)
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

	def test_sub_assembly_gets_its_own_bom_used_in_the_finished_good_bom(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		frame = get_part(design, "FRAME-ASM").node_id
		add_material(design, part="TUBE-25", quantity=3, bom=frame)
		add_material(design, part="BOLT-M6", quantity=4, bom=frame)
		add_material(design, part="FRAME-ASM", quantity=1)
		add_material(design, part="WHEEL-26", quantity=2)
		design.save()

		boms = make_boms(design)

		self.assertEqual(get_bom_items(boms["FRAME-ASM"]), {"TUBE-25": 3, "BOLT-M6": 4})
		finished_good_bom = frappe.get_doc("BOM", boms["BIKE-100"])
		self.assertEqual(
			{row.item_code: row.bom_no for row in finished_good_bom.items},
			{"FRAME-ASM": boms["FRAME-ASM"], "WHEEL-26": ""},
		)
		self.assertEqual([row.item_code for row in design.boms], ["FRAME-ASM", "BIKE-100"])
		self.assertEqual(design.status, "Completed")

	def test_create_boms_lists_every_problem(self):
		design = make_approved_design()
		design.track_semi_finished_goods = 1
		operation = add_operation(design, "_Test Design Welding", workstation_type="")
		add_material(design, part="TUBE-25", quantity=3, operation=operation)
		design.save()

		with self.assertRaises(frappe.ValidationError) as error:
			design.create_boms()

		self.assertIn("map an item before creating its BOM", str(error.exception))
		self.assertIn("set the Workstation Type", str(error.exception))
		self.assertIn("map an item for every raw material", str(error.exception))

	def test_material_needs_exactly_one_source(self):
		design = make_design()
		design.append("materials", {"item_code": "_Test Item", "part_node_id": 1, "quantity": 1})

		self.assertRaises(frappe.ValidationError, design.save)

	def test_operation_output_is_used_only_when_each_operation_makes_an_item(self):
		design = make_design()
		welding = add_operation(design, "_Test Design Welding")
		assembly = add_operation(design, "_Test Design Assembly")
		design.append("materials", {"from_operation_id": welding, "operation_id": assembly, "quantity": 1})

		self.assertRaises(frappe.ValidationError, design.save)

	def test_new_revision_keeps_edited_quantity_until_the_design_changes_it(self):
		design = make_mapped_design()
		get_part(design, "TUBE-25").quantity = 5
		get_part(design, "BOLT-M6", parent="FRAME-ASM").quantity = 10
		design.save()

		revision = frappe.get_doc("Engineering Design", design.make_new_revision())
		revision.design_file = make_step_file(
			BICYCLE_PRODUCTS,
			[
				link if link != ("FRAME-ASM", "BOLT-M6", 4) else ("FRAME-ASM", "BOLT-M6", 6)
				for link in BICYCLE_LINKS
			],
		)
		revision.save()

		self.assertEqual(
			(get_part(revision, "TUBE-25").quantity, get_part(revision, "TUBE-25").design_quantity), (5, 3)
		)
		bolt = get_part(revision, "BOLT-M6", parent="FRAME-ASM")
		self.assertEqual((bolt.quantity, bolt.design_quantity, bolt.change_type), (10, 6, "Quantity Changed"))

	def test_create_boms_needs_approval(self):
		design = make_design()

		self.assertRaises(frappe.ValidationError, design.create_boms)

	def test_part_model_must_be_a_supported_3d_file(self):
		for model_file, is_valid in (("/files/handle.pdf", False), ("/files/handle.glb", True)):
			design = make_design()
			design.append(
				"parts",
				{
					"part_number": "_Test Item",
					"item_code": "_Test Item",
					"quantity": 1,
					"model_file": model_file,
					"placements": '[{"position": [0, 10, 0], "quaternion": [0, 0, 0, 1]}]',
				},
			)

			if is_valid:
				design.save()
			else:
				self.assertRaises(frappe.ValidationError, design.save)

	def test_create_items_makes_items_only_for_parts_used_in_boms(self):
		design = make_approved_design()
		design.track_semi_finished_goods = 1
		add_material(design, part="TUBE-25", quantity=3)
		design.save()
		design.create_items(item_group="_Test Item Group", stock_uom="Nos")

		self.assertEqual(design.item_code, "BIKE-100")
		self.assertEqual(get_part(design, "TUBE-25").item_code, "TUBE-25")
		self.assertFalse(get_part(design, "WHEEL-26").item_code)

	def test_parts_from_approved_design_file_cannot_be_removed(self):
		design = make_approved_design()
		design.parts = [row for row in design.parts if row.part_number != "WHEEL-26"]

		self.assertRaises(frappe.ValidationError, design.save)

	def test_new_revision_keeps_mapping_materials_and_shows_changes(self):
		design = make_mapped_design(produce_item_at_each_operation=True)
		add_material(design, part="TUBE-25", quantity=3, bom=get_part(design, "FRAME-ASM").node_id)
		add_material(design, part="WHEEL-26", quantity=2)
		design.save()

		revision = frappe.get_doc("Engineering Design", design.make_new_revision())
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


def make_design():
	return frappe.get_doc(
		{
			"doctype": "Engineering Design",
			"company": "_Test Company",
			"design_file": make_step_file(BICYCLE_PRODUCTS, BICYCLE_LINKS),
		}
	).insert()


def make_approved_design():
	design = make_design()
	design.submit()
	return design


def make_mapped_design(produce_item_at_each_operation: bool = False):
	design = make_approved_design()
	design.track_semi_finished_goods = 1 if produce_item_at_each_operation else 0
	for part in design.parts:
		part.item_code = make_item(part.part_number, {"is_stock_item": 1}).name

	design.item_code = make_item("BIKE-100", {"is_stock_item": 1}).name
	design.save()
	return design


def add_operation(design, operation: str, workstation_type: str = "_Test Design Bench", **values) -> int:
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


def add_material(design, part: str, quantity: float, operation: int = 0, bom: int = 0):
	design.append(
		"materials",
		{
			"bom_node_id": bom,
			"operation_id": operation,
			"part_node_id": get_part(design, part).node_id,
			"quantity": quantity,
		},
	)


def make_boms(design) -> dict:
	design.create_boms()
	design.reload()
	return {row.item_code: row.bom for row in design.boms}


def get_part(design, part_number: str, parent: str | None = None):
	parent_node_ids = {row.node_id for row in design.parts if row.part_number == parent}
	return next(
		row
		for row in design.parts
		if row.part_number == part_number and (not parent or row.parent_node_id in parent_node_ids)
	)


def get_bom_items(bom: str) -> dict:
	return {row.item_code: row.qty for row in frappe.get_doc("BOM", bom).items}
