# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from six import string_types
from frappe import _, bold
from frappe.utils import add_days, today
from frappe.model.document import Document

class EmployeeGrievance(Document):
	def on_submit(self):
		if self.status not in ["Invalid", "Resolved"]:
			frappe.throw(_("Only Employee Grievance with status {0} and {1} can be submitted").format(
				bold("Invalid"),
				bold("Resolved"))
			)


