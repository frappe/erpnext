# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
from frappe.utils import flt, get_datetime, nowdate, cint, datetime, date_diff, time_diff

class VehicleRequest(Document):
	def validate(self):
		self.check_duplicate_entry()
		self.calculate_time()
		self.check_date()
		self.fetch_departrure_time()
		if self.kilometer_reading:
			if flt(self.previous_km) > flt(self.kilometer_reading):
				frappe.throw("Kilometer reading must be greater than previous kilometer reading.")

	def check_duplicate_entry(self):
		data = frappe.db.sql("""
			SELECT vehicle
			FROM `tabVehicle Request`
			WHERE vehicle = '{0}'
			AND docstatus = 1
			AND (from_date BETWEEN '{1}' AND '{2}'
				OR to_date BETWEEN '{1}' AND '{2}')
		""".format(self.vehicle,self.from_date,self.to_date),as_dict=1)
		if data:
			frappe.throw("Vehicle <b>{}</b> is already booked".format(self.vehicle_number))

	def calculate_time(self):
		time = time_diff(self.to_date, self.from_date)
		self.total_days_and_hours=time
		return time  

	def fetch_departrure_time(self):
		if self.workflow_state == "Waiting Approval":
			get_time = self.from_date
			self.time_of_departure = get_time  

	def  check_date(self):
		if self.from_date > self.to_date:
			frappe.throw("From Date cannot be before than To Date")

@frappe.whitelist()  
def check_form_date_and_to_date(from_date, to_date):
	if from_date > to_date:
		frappe.throw("From Date cannot be before than To Date")
@frappe.whitelist()
def create_logbook(source_name, target_doc=None):
	doclist = get_mapped_doc("Vehicle Request", source_name, {
		"Vehicle Request": {
			"doctype": "Vehicle Logbook"
		},
	}, target_doc)

	return doclist

@frappe.whitelist()
def get_previous_km(vehicle, vehicle_number):
	return frappe.db.sql(""" 
	SELECT 
		vr.kilometer_reading as km
	FROM `tabVehicle Request` vr 
	WHERE vr.vehicle ='{}' and vr.vehicle_number='{}' 
	ORDER BY vr.creation DESC LIMIT 1 """.format(vehicle, vehicle_number),as_dict=1)

@frappe.whitelist()
def create_vr_extension(source_name, target_doc=None):
	doclist = get_mapped_doc("Vehicle Request", source_name, {
		"Vehicle Request": {
			"doctype": "Vechicle Request Extension",
			"field_map": {
				"vehicle_request": "name",
				"from_date":"from_date",
				"to_date":"to_date"
			}
		},
	}, target_doc)

	return doclist

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return
	if "ADM User" in user_roles or  "Branch Manager" in user_roles or "Fleet Manager" in user_roles:
		return """(
			exists(select 1
				from `tabEmployee` as e
				where e.branch = `tabVehicle Request`.branch
				and e.user_id = '{user}')
			or
			exists(select 1
				from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
				where e.user_id = '{user}'
				and ab.employee = e.name
				and bi.parent = ab.name
				and bi.branch = `tabVehicle Request`.branch)
		)""".format(user=user)
	else:
		return """(
			exists(select 1
				from `tabEmployee` as e
				where e.name = `tabVehicle Request`.employee
				and e.user_id = '{user}')
		)""".format(user=user)