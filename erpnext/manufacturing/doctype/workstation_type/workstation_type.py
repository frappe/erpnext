# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WorkstationType(Document):
	def before_save(self):
		self.set_hour_rate()

	def set_hour_rate(self):
		self.hour_rate = (
			flt(self.hour_rate_labour)
			+ flt(self.hour_rate_electricity)
			+ flt(self.hour_rate_consumable)
			+ flt(self.hour_rate_rent)
		)


def get_workstations(workstation_type):
	workstations = frappe.get_all("Workstation", filters={"workstation_type": workstation_type})

	return [workstation.name for workstation in workstations]
