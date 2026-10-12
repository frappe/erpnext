# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import flt


class WorkstationType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.workstation_cost.workstation_cost import WorkstationCost

		description: DF.SmallText | None
		hour_rate: DF.Currency
		workstation_costs: DF.Table[WorkstationCost]
		workstation_type: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_operating_component()

	def validate_duplicate_operating_component(self):
		components = []
		for row in self.workstation_costs:
			if row.operating_component not in components:
				components.append(row.operating_component)
			else:
				frappe.throw(
					_("Duplicate Operating Component {0} found in Operating Components").format(
						bold(row.operating_component)
					)
				)

	def before_save(self):
		self.set_hour_rate()

	def set_hour_rate(self):
		self.hour_rate = 0.0

		for row in self.workstation_costs:
			if row.operating_cost:
				self.hour_rate += flt(row.operating_cost)

	def on_update(self):
		self.update_workstation_costs()

	def update_workstation_costs(self):
		previous = self.get_doc_before_save()
		if not previous:
			return

		old_costs = get_cost_map(previous.workstation_costs)
		if old_costs == get_cost_map(self.workstation_costs):
			return

		for name in self.get_workstations_with_costs(old_costs):
			workstation = frappe.get_doc("Workstation", name)
			workstation.workstation_costs = []
			for row in self.workstation_costs:
				workstation.append(
					"workstation_costs",
					{"operating_component": row.operating_component, "operating_cost": row.operating_cost},
				)
			workstation.save()

	def get_workstations_with_costs(self, costs):
		workstation = frappe.qb.DocType("Workstation")
		cost = frappe.qb.DocType("Workstation Cost")
		rows = (
			frappe.qb.from_(workstation)
			.left_join(cost)
			.on((cost.parent == workstation.name) & (cost.parenttype == "Workstation"))
			.select(workstation.name, cost.operating_component, cost.operating_cost)
			.where(workstation.workstation_type == self.name)
			.run(as_dict=True)
		)

		workstation_costs = {}
		for row in rows:
			workstation_costs.setdefault(row.name, [])
			if row.operating_component:
				workstation_costs[row.name].append(row)

		return [name for name, rows in workstation_costs.items() if get_cost_map(rows) == costs]


def get_cost_map(rows):
	return {row.operating_component: flt(row.operating_cost) for row in rows}


def get_workstations(workstation_type):
	workstations = frappe.get_all(
		"Workstation", filters={"workstation_type": workstation_type, "disabled": 0}, order_by="creation"
	)

	return [workstation.name for workstation in workstations]
