# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

COST_FIELDS = ("hour_rate_labour", "hour_rate_electricity", "hour_rate_consumable", "hour_rate_rent")


class WorkstationType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		hour_rate: DF.Currency
		hour_rate_consumable: DF.Currency
		hour_rate_electricity: DF.Currency
		hour_rate_labour: DF.Currency
		hour_rate_rent: DF.Currency
		workstation_type: DF.Data
	# end: auto-generated types

	def before_save(self):
		self.set_hour_rate()

	def set_hour_rate(self):
		self.hour_rate = (
			flt(self.hour_rate_labour)
			+ flt(self.hour_rate_electricity)
			+ flt(self.hour_rate_consumable)
			+ flt(self.hour_rate_rent)
		)

	def on_update(self):
		self.update_workstation_costs()

	def update_workstation_costs(self):
		previous = self.get_doc_before_save()
		if not previous:
			return

		old_costs = get_cost_map(previous)
		new_costs = get_cost_map(self)
		if old_costs == new_costs:
			return

		self.clear_cache()
		for name in self.get_workstations_with_costs(old_costs):
			workstation = frappe.get_doc("Workstation", name)
			workstation.update(new_costs)
			workstation.save()

	def get_workstations_with_costs(self, costs):
		workstations = frappe.get_all(
			"Workstation", filters={"workstation_type": self.name}, fields=["name", *COST_FIELDS]
		)

		return [row.name for row in workstations if get_cost_map(row) == costs]


def get_cost_map(doc):
	return {field: flt(doc.get(field)) for field in COST_FIELDS}


def get_workstations(workstation_type):
	workstations = frappe.get_all(
		"Workstation", filters={"workstation_type": workstation_type}, order_by="creation"
	)

	return [workstation.name for workstation in workstations]
