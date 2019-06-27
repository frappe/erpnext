# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _

class JobOffer(Document):
	def onload(self):
		employee = frappe.db.get_value("Employee", {"job_applicant": self.job_applicant}, "name") or ""
		self.set_onload("employee", employee)

	def validate(self):
		self.validate_vacancies()

	def validate_vacancies(self):
		staffing_plan = get_staffing_plan_detail(self.designation, self.company, self.offer_date)
		check_vacancies = frappe.get_single("HR Settings").check_vacancies
		if staffing_plan and check_vacancies:
			vacancies = frappe.db.get_value("Staffing Plan Detail", filters={"name": staffing_plan.name}, fieldname=['staffing_plan'])
			no_of_job_offer = len(self.get_job_offer(staffing_plan.from_date, staffing_plan.to_date))
			if vacancies - no_of_job_offer <= 0:
				frappe.throw(_("Not enough vacancies available. Please update the staffing plan!!!"))

	def get_job_offer(self, from_date, to_date):
		''' Returns job offer created during a time period '''
		return frappe.get_all("Job Offer", filters={
				"offer_date": ['between', (from_date, to_date)],
				"designation": self.designation,
				"company": self.company
			}, fields=['name'])

def get_staffing_plan_detail(designation, company, offer_date):
	detail = frappe.db.sql("""
		SELECT spd.name as name,
			sp.from_date as from_date,
			sp.to_date as to_date
		FROM `tabStaffing Plan Detail` spd, `tabStaffing Plan` sp
		WHERE
			sp.docstatus=1
			AND spd.designation=%s
			AND sp.company=%s
			AND %s between sp.from_date and sp.to_date
	""", (designation, company, offer_date), as_dict=1)
	return detail[0].get("name") if detail else None

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
	doc = get_mapped_doc("Job Offer", source_name, {
			"Job Offer": {
				"doctype": "Employee",
				"field_map": {
					"applicant_name": "employee_name",
				}}
		}, target_doc, set_missing_values)
	return doc