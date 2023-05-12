# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.hr.utils import validate_active_employee
from frappe.core.doctype.user.user import share_doc_with_approver


class TravelRequest(Document):
	def autoname(self):
		self.name =  make_autoname(self.employee + "/" +(str(self.date)) + "/" + ".##")
		self.requition_no = make_autoname(self.employee_name + "-.##")
        
	def validate(self):
		validate_active_employee(self.employee)
	
	def on_submit(self):
		if self.status != "Approved":
			frappe.throw(("Document status must be 'Approved' before submitting."))

	def on_update(self):
		if self.status == "Approved":
			name = frappe.get_doc("Travel Request", self.name)
			name.submit()
			self.reload()


@frappe.whitelist()
def report_to_person_view_travel_request_form(name,approving_officer):
	get_travel_request_form = frappe.get_doc("Travel Request",name)
	share_doc_with_approver(get_travel_request_form, approving_officer)

@frappe.whitelist()
def get_grade_child_details(grade,mode):
	grade= frappe.get_doc("Employee Grade",grade)
	mode_data = []
	if mode == "Bus":
		for travel_mode in grade.get("bus"):
			mode_data.append(travel_mode.bus_table)
	elif mode == "Air Travel":
		for travel_mode in grade.get("air_travel"):
			mode_data.append(travel_mode.air_travel_table)
	elif mode == "Railway":
		for travel_mode in grade.get("railway"):
			mode_data.append(travel_mode.railway_table)
	elif mode == "Local":
		for travel_mode in grade.get("local"):
			mode_data.append(travel_mode.local_table)
	return mode_data 

