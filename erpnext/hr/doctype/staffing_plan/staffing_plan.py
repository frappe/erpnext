# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate

class StaffingPlan(Document):
	def validate(self):
		# Validate Dates
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be greater than To Date"))

		# Validate if any submitted Staffing Plan exist for Designations in this plan
		# and spd.vacancies>0 ?
		for detail in self.get("staffing_details"):
			overlap = (frappe.db.sql("""select spd.parent \
				from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name \
				where spd.designation='{0}' and sp.docstatus=1 \
				and sp.to_date >= '{1}' and sp.from_date <='{2}'""".format(detail.designation, self.from_date, self.to_date)))

			if overlap and overlap [0][0]:
				frappe.throw(_("Staffing Plan {0} already exist for designation {1}".format(overlap[0][0], detail.designation)))

@frappe.whitelist()
def get_current_employee_count(designation):
	if not designation:
		return False
	employee_count = frappe.db.sql("""select count(*) from `tabEmployee` where \
							designation = '{0}' and status='Active'""".format(designation))[0][0]
	return employee_count

@frappe.whitelist()
def get_active_staffing_plan_and_vacancies(company, designation, department=None, date=getdate(nowdate())):
	if not company or not designation:
		frappe.throw(_("Please select Company and Designation"))

	conditions = "spd.designation='{0}' and sp.docstatus=1 and \
	sp.company='{1}'".format(designation, company)

	if(department): #Department is an optional field
		conditions += " and sp.department='{0}'".format(department)

	if(date): #ToDo: Date should be mandatory?
		conditions += " and '{0}' between sp.from_date and sp.to_date".format(date)

	staffing_plan = frappe.db.sql("""select spd.parent, spd.vacancies \
		from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
		where {0}""".format(conditions))

	# Only a signle staffing plan can be active for a designation on given date
	return staffing_plan[0] if staffing_plan else False
