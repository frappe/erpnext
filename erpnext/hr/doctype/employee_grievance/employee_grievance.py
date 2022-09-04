# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document


class EmployeeGrievance(Document):
	def on_submit(self):
		if self.status not in ["Invalid", "Resolved"]:
			frappe.throw(
				_("Only Employee Grievance with status {0} or {1} can be submitted").format(
					bold("Invalid"), bold("Resolved")
				)
			)
