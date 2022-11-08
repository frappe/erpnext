# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkstationType(Document):
	pass


def get_workstations(workstation_type):
	workstations = frappe.get_all("Workstation", filters={"workstation_type": workstation_type})

	return [workstation.name for workstation in workstations]
