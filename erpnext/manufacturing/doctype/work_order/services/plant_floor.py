import frappe
from frappe import _
from frappe.utils import cint, flt


class PlantFloorService:
	def __init__(self, doc):
		self.doc = doc

	@property
	def plant_floor(self):
		if not hasattr(self, "_plant_floor"):
			self._plant_floor = frappe.get_doc("Plant Floor", self.doc.plant_floor)
		return self._plant_floor

	def sync(self, previous):
		if self.doc.docstatus != 0:
			return

		self.validate_company()
		if self.has_plan_changed(previous):
			self.validate_plant_floor()
			self.set_items_and_operations()

	def has_plan_changed(self, previous):
		if previous is None or not self.doc.operations:
			return True
		return previous.plant_floor != self.doc.plant_floor or flt(previous.qty) != flt(self.doc.qty)

	def validate_company(self):
		company = self.plant_floor.company
		if company and self.doc.company and company != self.doc.company:
			frappe.throw(
				_("Plant Floor {0} belongs to company {1}, not {2}").format(
					frappe.bold(self.plant_floor.name), frappe.bold(company), frappe.bold(self.doc.company)
				)
			)

	def validate_plant_floor(self):
		plant_floor = self.plant_floor
		if self.doc.production_item != plant_floor.production_item:
			frappe.throw(
				_("Plant Floor {0} makes {1}, not {2}").format(
					frappe.bold(plant_floor.name),
					frappe.bold(plant_floor.production_item),
					frappe.bold(self.doc.production_item),
				)
			)

		if errors := plant_floor.setup_errors:
			frappe.throw(
				errors, title=_("Finish the setup of Plant Floor {0}").format(plant_floor.name), as_list=True
			)

	def set_items_and_operations(self):
		plan = self.plant_floor.get_batch_plan(self.doc.qty)
		stages = plan.get_stages()
		self.set_work_order_values(stages)
		self.set_operations(stages)
		self.set_required_items(plan, stages)

	def set_work_order_values(self, stages):
		self.doc.update(
			{
				"company": self.plant_floor.company or self.doc.company,
				"track_semi_finished_goods": 1,
				"transfer_material_against": "Job Card",
				"skip_transfer": 0,
				"from_wip_warehouse": 0,
				"use_multi_level_bom": 0,
				"source_warehouse": None,
				"wip_warehouse": stages[0].warehouse,
				"fg_warehouse": self.plant_floor.fg_warehouse,
			}
		)

	def set_operations(self, stages):
		templates = get_inspection_templates([stage.operation for stage in stages])
		self.doc.set("operations", [])
		for stage in stages:
			self.doc.append(
				"operations",
				{
					"operation": stage.operation,
					"description": stage.stage_name,
					"workstation": stage.workstation,
					"time_in_mins": stage.time_in_mins,
					"finished_good": stage.output_item,
					"output_qty": 0 if stage.is_packing else stage.output_qty,
					"wip_warehouse": stage.warehouse,
					"fg_warehouse": self.plant_floor.fg_warehouse if stage.is_packing else stage.warehouse,
					"sequence_id": stage.sequence_id,
					"status": "Pending",
					"quality_inspection_required": cint(bool(templates.get(stage.operation))),
				},
			)

	def set_required_items(self, plan, stages):
		materials, store, rows = plan.get_materials(), self.plant_floor.warehouse, []
		for stage in stages:
			for source in stage.inputs:
				rows.append(self.get_row(source, stage, stages[source.stage_idx - 1].warehouse))
			rows.extend(self.get_row(row, stage, store) for row in materials if row.stage_row_id == stage.idx)

		rows.extend(self.get_row(row, stages[-1], store) for row in plan.get_packing_materials())
		self.set_item_details(rows)
		self.doc.set("required_items", rows)

	@staticmethod
	def get_row(row, stage, source_warehouse):
		return {
			"item_code": row.item_code,
			"required_qty": row.qty,
			"source_warehouse": source_warehouse,
			"operation": stage.operation,
			"operation_row_id": stage.idx,
			"include_item_in_manufacturing": 1,
		}

	@staticmethod
	def set_item_details(rows):
		details = {
			item.name: item
			for item in frappe.get_all(
				"Item",
				filters={"name": ("in", [row["item_code"] for row in rows])},
				fields=["name", "item_name", "stock_uom", "description"],
			)
		}
		for row in rows:
			item = details[row["item_code"]]
			row.update(item_name=item.item_name, stock_uom=item.stock_uom, description=item.description)


def get_inspection_templates(operations):
	return dict(
		frappe.get_all(
			"Operation",
			filters={"name": ("in", operations)},
			fields=["name", "quality_inspection_template"],
			as_list=1,
		)
	)
