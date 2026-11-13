# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user

from erpnext.manufacturing.doctype.bom_creator.process_formula import ProcessFormula
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.tests.utils import ERPNextTestSuite

STORE = "Stores - _TC"
FINISHED_GOODS = "Finished Goods - _TC"


class TestProcessDesign(ERPNextTestSuite):
	def test_formula_tops_up_the_balance_item_and_sets_stage_outputs(self):
		design = make_ketchup_design()

		materials = {row.item_code: row for row in design.materials}
		self.assertEqual(materials["_Test Process Water"].qty * 2000, 375)
		self.assertEqual(materials["_Test Process Water"].uom, "Litre")
		self.assertEqual(
			[round(row.output_quantity * 2000, 3) for row in design.operations], [1250, 1000, 2000]
		)
		self.assertEqual([row.sequence_id for row in design.operations], [1, 2, 3])
		self.assertEqual(ProcessFormula(design).get_problems(), [])

	def test_process_bom_carries_machines_warehouses_and_stage_inputs(self):
		bom = frappe.get_doc("BOM", make_ketchup_bom(make_ketchup_design()))

		self.assertTrue(bom.track_semi_finished_goods)
		self.assertEqual((bom.formula_tolerance, bom.default_source_warehouse), (2, None))
		self.assertEqual(bom.backflush_based_on, "Material Transferred for Manufacture")
		self.assertEqual(
			[(row.workstation, row.wip_warehouse, row.fg_warehouse) for row in bom.operations],
			[
				("_Test Mixer", "_Test Mixer Warehouse - _TC", "_Test Mixer Warehouse - _TC"),
				("_Test Kettle", "_Test Kettle Warehouse - _TC", "_Test Kettle Warehouse - _TC"),
				("_Test Filler", "_Test Filler Warehouse - _TC", None),
			],
		)
		items = {(row.operation_row_id, row.item_code): row for row in bom.items}
		self.assertEqual(items[(1, "_Test Tomato Paste")].qty, 500)
		self.assertEqual(items[(1, "_Test Tomato Paste")].source_warehouse, STORE)
		self.assertTrue(items[(1, "_Test Process Water")].is_balance_item)
		self.assertEqual(items[(2, "_Test Ketchup Pre-mix")].qty, 1250)
		self.assertEqual(items[(2, "_Test Ketchup Pre-mix")].source_warehouse, "_Test Mixer Warehouse - _TC")
		self.assertEqual(items[(3, "_Test Cooked Ketchup Base")].qty, 1000)
		self.assertEqual(items[(3, "_Test Ketchup PET Bottle")].qty, 2000)

	def test_problems_list_what_is_missing(self):
		design = make_ketchup_design()
		design.materials[1].is_balance_item = 0
		design.materials[1].qty = 0.1
		self.assertIn(
			"The formula makes 860.0 Kg but the batch needs 1000.0 Kg. Change a quantity or pick a balance item.",
			ProcessFormula(design).get_problems(),
		)

		design.operations[2].workstation = "_Test Mixer"
		problems = ProcessFormula(design).get_problems()
		self.assertIn("End with exactly one packing stage, a Filling Line or a Bagging Line", problems)

	def test_each_stage_makes_its_own_semi_finished_good(self):
		design = make_ketchup_design()
		design.operations[1].output_item = "_Test Ketchup Pre-mix"

		self.assertIn(
			"_Test Ketchup Pre-mix is made by more than one stage. Give each stage its own semi-finished good.",
			ProcessFormula(design).get_problems(),
		)

	def test_formula_keeps_rows_it_cannot_use_and_reports_them(self):
		design = make_ketchup_design()
		design.append("materials", {"operation_id": 2, "from_operation_id": 1, "qty": 0.625})
		design.materials[0].uom = "Gram"
		design.save()

		self.assertEqual(design.materials[0].uom, "Gram")
		self.assertTrue([row for row in design.materials if row.from_operation_id])
		problems = design.get_bom_plan().get_problems()
		self.assertIn(
			"Remove the stage outputs from the materials. Each stage passes its output on by Sequence ID.",
			problems,
		)
		self.assertIn("Use the stock UOM Kg for _Test Tomato Paste", problems)

	def test_parallel_stages_split_the_next_stage_inputs(self):
		design = make_parallel_ketchup_design()
		formula = ProcessFormula(design)

		self.assertEqual(formula.get_problems(), [])
		self.assertEqual([row.sequence_id for row in design.operations], [1, 1, 2, 3])
		inputs = [
			(row.stage.operation, row.source.output_item, round(row.qty * 2000, 3))
			for row in formula.get_stage_inputs()
		]
		self.assertIn(("_Test Kettle Operation", "_Test Ketchup Spice Mix", 62.5), inputs)
		self.assertIn(("_Test Kettle Operation", "_Test Ketchup Pre-mix", 1187.5), inputs)

	def test_problems_for_parallel_stages(self):
		design = make_parallel_ketchup_design()
		design.operations[2].sequence_id = 3
		design.operations[3].sequence_id = 3
		for row in design.materials:
			if row.item_code == "_Test Ketchup Spices":
				row.operation_id = 2
		problems = ProcessFormula(design).get_problems()

		self.assertIn("Stage 3 needs Sequence ID 1 or 2", problems)
		self.assertIn("The packing stage runs on its own, after all other stages", problems)
		self.assertIn("Stage 1 starts the process, so give it at least one raw material", problems)

	def test_plant_builder_checks_an_unsaved_design(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_design

		design = make_ketchup_design().as_dict()
		design.update(name=None, raw_material_warehouse=None)
		result = check_design(design)

		self.assertIn("Set the Raw Material Warehouse", result["errors"])
		self.assertEqual(result["balance_qty"], 375)
		self.assertIn("_Test Mixer", result["machines"])
		self.assertEqual(result["items"]["_Test Process Water"].stock_uom, "Litre")
		self.assertEqual(result["formula_weight"], 1250)

	def test_plant_builder_checks_a_design_it_cannot_compute_yet(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_design

		design = make_ketchup_design().as_dict()
		design.operations[0].update(yield_percentage=0, output_quantity=None)
		result = check_design(design)

		self.assertIn("Stage 1 needs a yield above 0% and up to 100%", result["errors"])
		self.assertEqual(result["outputs"][1], 0)

	def test_plant_builder_design_check_lists_what_blocks_the_boms(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_design

		design = make_ketchup_design().as_dict()
		design.operations[0].update(output_item=None, time_in_mins=0)
		errors = "\n".join(check_design(design)["errors"])

		self.assertIn("choose the item this step makes", errors)
		self.assertIn("set the operation time", errors)

	def test_plant_builder_design_check_needs_workstation_read(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_design

		design = make_ketchup_design().as_dict()
		user = create_user("plant-builder-designer@example.com", "Manufacturing Manager")
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("BOM Creator", "read"))
			self.assertRaises(frappe.PermissionError, check_design, design)


def make_ketchup_items():
	for item_code, stock_uom in (
		("_Test Tomato Paste", "Kg"),
		("_Test Ketchup Sugar", "Kg"),
		("_Test Ketchup Pre-mix", "Kg"),
		("_Test Ketchup PET Bottle", "Nos"),
	):
		make_item(item_code, {"is_stock_item": 1, "stock_uom": stock_uom, "valuation_rate": 10})

	make_item(
		"_Test Cooked Ketchup Base",
		{
			"is_stock_item": 1,
			"stock_uom": "Kg",
			"valuation_rate": 10,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "_TKB-.#####",
		},
	)

	make_item(
		"_Test Process Water",
		{"is_stock_item": 1, "stock_uom": "Litre", "valuation_rate": 1},
		uoms=[{"uom": "Kg", "conversion_factor": 1}],
	)
	make_item(
		"_Test Ketchup Bottle",
		{"is_stock_item": 1, "stock_uom": "Nos", "weight_per_unit": 0.5, "weight_uom": "Kg"},
	)
	return "_Test Ketchup Bottle"


def make_machine(name, machine_model):
	workstation_type = f"_Test {name} Type"
	if not frappe.db.exists("Workstation Type", workstation_type):
		frappe.get_doc(
			{
				"doctype": "Workstation Type",
				"workstation_type": workstation_type,
				"machine_model": machine_model,
			}
		).insert()

	warehouse = create_warehouse(f"_Test {name} Warehouse")
	if not frappe.db.exists("Workstation", f"_Test {name}"):
		frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": f"_Test {name}",
				"workstation_type": workstation_type,
				"warehouse": warehouse,
			}
		).insert()

	if not frappe.db.exists("Operation", f"_Test {name} Operation"):
		frappe.get_doc({"doctype": "Operation", "name": f"_Test {name} Operation"}).insert()

	return f"_Test {name}", f"_Test {name} Operation", workstation_type


def get_stage(operation_id, name, machine_model, output_item=None, yield_percentage=100):
	workstation, operation, workstation_type = make_machine(name, machine_model)
	return {
		"operation_id": operation_id,
		"operation": operation,
		"workstation": workstation,
		"workstation_type": workstation_type,
		"time_in_mins": 30,
		"output_item": output_item,
		"yield_percentage": yield_percentage,
	}


def make_ketchup_design(batch_size=2000):
	production_item = make_ketchup_items()
	return frappe.get_doc(
		{
			"doctype": "BOM Creator",
			"design_name": "_Test Ketchup Design",
			"item_code": production_item,
			"company": "_Test Company",
			"track_semi_finished_goods": 1,
			"qty": batch_size,
			"raw_material_warehouse": STORE,
			"formula_tolerance": 2,
			"operations": [
				get_stage(1, "Mixer", "Mixer", "_Test Ketchup Pre-mix"),
				get_stage(2, "Kettle", "Steam Kettle", "_Test Cooked Ketchup Base", 80),
				get_stage(3, "Filler", "Filling Line"),
			],
			"materials": [
				{"operation_id": 1, "item_code": "_Test Tomato Paste", "qty": 0.25},
				{"operation_id": 1, "item_code": "_Test Process Water", "qty": 0, "is_balance_item": 1},
				{"operation_id": 1, "item_code": "_Test Ketchup Sugar", "qty": 0.1875},
				{"operation_id": 3, "item_code": "_Test Ketchup PET Bottle", "qty": 1},
			],
		}
	).insert()


def make_parallel_ketchup_design():
	for item_code in ("_Test Ketchup Spices", "_Test Ketchup Spice Mix"):
		make_item(item_code, {"is_stock_item": 1, "stock_uom": "Kg", "valuation_rate": 10})

	design = make_ketchup_design()
	mill = get_stage(4, "Mill", "Mill", "_Test Ketchup Spice Mix")
	design.operations = []
	for sequence_id, stage in zip(
		(1, 1, 2, 3),
		(
			mill,
			get_stage(1, "Mixer", "Mixer", "_Test Ketchup Pre-mix"),
			get_stage(2, "Kettle", "Steam Kettle", "_Test Cooked Ketchup Base", 80),
			get_stage(3, "Filler", "Filling Line"),
		),
		strict=True,
	):
		design.append("operations", {**stage, "sequence_id": sequence_id})

	sugar = next(row for row in design.materials if row.item_code == "_Test Ketchup Sugar")
	sugar.qty = 0.15625
	design.append("materials", {"operation_id": 4, "item_code": "_Test Ketchup Spices", "qty": 0.03125})
	design.save()
	return design


def make_ketchup_bom(design):
	return design.get_bom_plan().make_boms()[design.item_code]


def make_process_work_order(bom_no, qty, insert=True):
	work_order = frappe.new_doc("Work Order")
	work_order.update(
		{
			"production_item": frappe.db.get_value("BOM", bom_no, "item"),
			"bom_no": bom_no,
			"qty": qty,
			"company": "_Test Company",
			"wip_warehouse": "_Test Warehouse - _TC",
			"fg_warehouse": FINISHED_GOODS,
		}
	)
	work_order.get_items_and_operations_from_bom()
	if insert:
		work_order.insert()
	return work_order


def stock_ketchup_materials():
	make_ketchup_items()
	for item_code, qty in (
		("_Test Tomato Paste", 2000),
		("_Test Process Water", 2000),
		("_Test Ketchup Sugar", 2000),
		("_Test Ketchup PET Bottle", 3000),
	):
		make_stock_entry(item_code=item_code, target=STORE, qty=qty, basic_rate=10)
