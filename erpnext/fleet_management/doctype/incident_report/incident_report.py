# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.custom_utils import check_future_date
from frappe.model.document import Document

class IncidentReport(Document):
	def validate(self):
		check_future_date(self.offence_date)
