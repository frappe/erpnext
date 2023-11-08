# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.model.naming import make_autoname
from datetime import datetime
from erpnext.hr.utils import validate_overlap


class LeavePeriod(Document):
	def validate(self):
		self.validate_dates()
		validate_overlap(self, self.date_from, self.date_to, self.company)

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))
	def autoname(self):
		to_date_dt = getdate(self.to_date)
		to_date_year = to_date_dt.year
		last_numbers = frappe.get_all("Leave Period", filters={"name": ["like", f"AXIS-LPR-{to_date_year}-%"]}, fields=["name"])
		if last_numbers:
			last_numbers = [entry.get("name") for entry in last_numbers]
			last_numbers = sorted(last_numbers)  # Sort the existing names
			latest_name = last_numbers[-1]
			parts = latest_name.split("-")
			if len(parts) >= 4:
				last_year = int(parts[-2])
				last_number = int(parts[-1])
				if last_year == to_date_year:
					next_number = last_number + 1
				else:
					next_number = 1
			else:
				next_number = 1
		else:
			next_number = 1
		generated_name = f"AXIS-LPR-{to_date_year}-{next_number:02d}"
		self.name = generated_name