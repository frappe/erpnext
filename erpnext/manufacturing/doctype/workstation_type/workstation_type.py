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


def get_workstations(workstation_type):
	workstations = frappe.get_all(
		"Workstation", filters={"workstation_type": workstation_type}, order_by="creation"
	)

	return [workstation.name for workstation in workstations]
