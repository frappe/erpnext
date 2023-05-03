# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.hr.utils import validate_active_employee


class TravelRequest(Document):
	def autoname(self):
		self.name =  make_autoname(self.employee + "/" +(str(self.date)) + "/" + ".##")
		self.requition_no = make_autoname(self.employee_name + "-.##")
        
	def validate(self):
		validate_active_employee(self.employee)




@frappe.whitelist()
def get_grade_child_details(grade,mode):
	grade= frappe.get_doc("Employee Grade",grade)
	person_data = []
	if mode == "Bus":
		for person in grade.get("bus"):
			person_data.append(person.bus_table)
	elif mode == "Air Travel":
		for person in grade.get("air_travel"):
			person_data.append(person.air_travel_table)
	elif mode == "Railway":
		for person in grade.get("railway"):
			person_data.append(person.railway_table)
	elif mode == "Local":
		for person in grade.get("local"):
			person_data.append(person.local_table)
	return person_data 

