import frappe
from frappe import _
from frappe.utils import flt


class PlantSetupCheck:
	def __init__(self, plant_floor):
		self.plant_floor = plant_floor
		self.plan = plant_floor.get_batch_plan()

	def get_errors(self):
		return [*self.get_product_errors(), *self.get_formula_errors(), *self.get_stage_errors()]

	def get_product_errors(self):
		plant_floor, errors = self.plant_floor, []
		if not plant_floor.production_item:
			return [_("Set the Finished Good")]
		if self.plan.weight_per_unit <= 0 or not self.plan.weight_uom:
			errors.append(_("Set Weight Per Unit and Weight UOM on {0}").format(plant_floor.production_item))
		if flt(plant_floor.batch_size) <= 0:
			errors.append(_("The batch size must be above zero"))
		if not plant_floor.warehouse:
			errors.append(_("Set the warehouse that holds the raw materials"))
		if not plant_floor.fg_warehouse:
			errors.append(_("Set the Finished Goods Warehouse"))
		return errors

	def get_formula_errors(self):
		materials, errors = self.plant_floor.materials, []
		if not materials:
			return [_("Add at least one raw material")]
		if any(not row.is_balance_item and flt(row.percentage) <= 0 for row in materials):
			errors.append(_("Every percentage must be above zero"))

		total = 100 - self.plan.balance_percentage
		has_balance = any(row.is_balance_item for row in materials)
		if has_balance and self.plan.balance_percentage <= 0:
			errors.append(
				_("The formula is {0}% before the balance item. Bring it under 100%.").format(flt(total, 3))
			)
		if not has_balance and abs(100 - total) > 0.001:
			errors.append(
				_("The formula adds up to {0}%. Make it 100% or pick a balance item.").format(flt(total, 3))
			)
		return errors + self.get_unit_errors(row.item_code for row in materials)

	def get_unit_errors(self, item_codes):
		if not self.plan.weight_uom:
			return []
		return [
			_("Add {0} to the units of measure of {1}").format(self.plan.weight_uom, item_code)
			for item_code in item_codes
			if item_code and not self.plan.weight_factors.get(item_code)
		]

	def get_stage_errors(self):
		stages = self.plant_floor.stages
		packing = [stage for stage in stages if self.plant_floor.is_packing_stage(stage)]
		errors = []
		if len(stages) - len(packing) < 1:
			errors.append(_("Add at least one process stage before packing"))
		if len(packing) != 1 or not self.plant_floor.is_packing_stage(stages[-1]):
			errors.append(_("End with exactly one packing stage, a Filling Line or a Bagging Line"))
		if packing and not self.plant_floor.packing_materials:
			errors.append(_("Add at least one packing material"))

		for stage in stages:
			errors.extend(self.get_errors_for_stage(stage))
		return errors

	def get_errors_for_stage(self, stage):
		errors = []
		if not self.plant_floor.machine_warehouses.get(stage.workstation):
			errors.append(_("Set a warehouse on workstation {0}").format(stage.workstation))
		if self.plant_floor.is_packing_stage(stage):
			return errors

		if not stage.semi_finished_good:
			errors.append(_("Stage {0} needs the semi-finished good it makes").format(stage.idx))
		if not 0 < flt(stage.yield_percentage) <= 100:
			errors.append(_("Stage {0} yield must be between 1 and 100%").format(stage.idx))
		return errors + self.get_unit_errors([stage.semi_finished_good])
