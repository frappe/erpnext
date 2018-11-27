# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, cint, flt

class SubsidiaryCompanyError(frappe.ValidationError): pass
class ParentCompanyError(frappe.ValidationError): pass

class StaffingPlan(Document):
	def validate(self):
		# Validate Dates
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be greater than To Date"))

		self.total_estimated_budget = 0

		for detail in self.get("staffing_details"):
			self.validate_overlap(detail)
			self.validate_with_subsidiary_plans(detail)
			self.validate_with_parent_plan(detail)

			#Set readonly fields
			designation_counts = get_designation_counts(detail.designation, self.company)
			detail.current_count = designation_counts['employee_count']
			detail.current_openings = designation_counts['job_openings']

			if detail.number_of_positions < (detail.current_count + detail.current_openings):
				frappe.throw(_("Number of positions cannot be less then current count of employees"))
			elif detail.number_of_positions > 0:
				detail.vacancies = detail.number_of_positions - (detail.current_count + detail.current_openings)
				if detail.vacancies > 0 and detail.estimated_cost_per_position:
					detail.total_estimated_cost = detail.vacancies * detail.estimated_cost_per_position
				else: detail.total_estimated_cost = 0
			else: detail.vacancies = detail.number_of_positions = detail.total_estimated_cost = 0
			self.total_estimated_budget += detail.total_estimated_cost

	def validate_overlap(self, staffing_plan_detail):
		# Validate if any submitted Staffing Plan exist for any Designations in this plan
		# and spd.vacancies>0 ?
		overlap = frappe.db.sql("""select spd.parent
			from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
			where spd.designation=%s and sp.docstatus=1
			and sp.to_date >= %s and sp.from_date <= %s and sp.company = %s
		""", (staffing_plan_detail.designation, self.from_date, self.to_date, self.company))
		if overlap and overlap [0][0]:
			frappe.throw(_("Staffing Plan {0} already exist for designation {1}"
				.format(overlap[0][0], staffing_plan_detail.designation)))

	def validate_with_parent_plan(self, staffing_plan_detail):
		if not frappe.get_cached_value('Company',  self.company,  "parent_company"):
			return # No parent, nothing to validate

		# Get staffing plan applicable for the company (Parent Company)
		parent_plan_details = get_active_staffing_plan_details(self.company, staffing_plan_detail.designation, self.from_date, self.to_date)
		if not parent_plan_details:
			return #no staffing plan for any parent Company in hierarchy

		# Fetch parent company which owns the staffing plan. NOTE: Parent could be higher up in the hierarchy
		parent_company = frappe.db.get_value("Staffing Plan", parent_plan_details[0].name, "company")
		# Parent plan available, validate with parent, siblings as well as children of staffing plan Company
		if cint(staffing_plan_detail.vacancies) > cint(parent_plan_details[0].vacancies) or \
			flt(staffing_plan_detail.total_estimated_cost) > flt(parent_plan_details[0].total_estimated_cost):
			frappe.throw(_("You can only plan for upto {0} vacancies and budget {1} \
				for {2} as per staffing plan {3} for parent company {4}."
				.format(cint(parent_plan_details[0].vacancies),
					parent_plan_details[0].total_estimated_cost,
					frappe.bold(staffing_plan_detail.designation),
					parent_plan_details[0].name,
					parent_company)), ParentCompanyError)

		#Get vacanices already planned for all companies down the hierarchy of Parent Company
		lft, rgt = frappe.get_cached_value('Company',  parent_company,  ["lft", "rgt"])
		all_sibling_details = frappe.db.sql("""select sum(spd.vacancies) as vacancies,
			sum(spd.total_estimated_cost) as total_estimated_cost
			from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
			where spd.designation=%s and sp.docstatus=1
			and sp.to_date >= %s and sp.from_date <=%s
			and sp.company in (select name from tabCompany where lft > %s and rgt < %s)
		""", (staffing_plan_detail.designation, self.from_date, self.to_date, lft, rgt), as_dict = 1)[0]

		if (cint(parent_plan_details[0].vacancies) < \
			(cint(staffing_plan_detail.vacancies) + cint(all_sibling_details.vacancies))) or \
			(flt(parent_plan_details[0].total_estimated_cost) < \
			(flt(staffing_plan_detail.total_estimated_cost) + flt(all_sibling_details.total_estimated_cost))):
			frappe.throw(_("{0} vacancies and {1} budget for {2} already planned for subsidiary companies of {3}. \
				You can only plan for upto {4} vacancies and and budget {5} as per staffing plan {6} for parent company {3}."
				.format(cint(all_sibling_details.vacancies),
					all_sibling_details.total_estimated_cost,
					frappe.bold(staffing_plan_detail.designation),
					parent_company,
					cint(parent_plan_details[0].vacancies),
					parent_plan_details[0].total_estimated_cost,
					parent_plan_details[0].name)))

	def validate_with_subsidiary_plans(self, staffing_plan_detail):
		#Valdate this plan with all child company plan
		children_details = frappe.db.sql("""select sum(spd.vacancies) as vacancies,
			sum(spd.total_estimated_cost) as total_estimated_cost
			from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
			where spd.designation=%s and sp.docstatus=1
			and sp.to_date >= %s and sp.from_date <=%s
			and sp.company in (select name from tabCompany where parent_company = %s)
		""", (staffing_plan_detail.designation, self.from_date, self.to_date, self.company), as_dict = 1)[0]

		if children_details and \
			cint(staffing_plan_detail.vacancies) < cint(children_details.vacancies) or \
			flt(staffing_plan_detail.total_estimated_cost) < flt(children_details.total_estimated_cost):
			frappe.throw(_("Subsidiary companies have already planned for {1} vacancies at a budget of {2}. \
				Staffing Plan for {0} should allocate more vacancies and budget for {3} than planned for its subsidiary companies"
				.format(self.company,
					cint(children_details.vacancies),
					children_details.total_estimated_cost,
					frappe.bold(staffing_plan_detail.designation))), SubsidiaryCompanyError)

@frappe.whitelist()
def get_designation_counts(designation, company):
	if not designation:
		return False

	employee_counts_dict = {}
	lft, rgt = frappe.get_cached_value('Company',  company,  ["lft", "rgt"])
	employee_counts_dict["employee_count"] = frappe.db.sql("""select count(*) from `tabEmployee`
		where designation = %s and status='Active'
			and company in (select name from tabCompany where lft>=%s and rgt<=%s)
		""", (designation, lft, rgt))[0][0]

	employee_counts_dict['job_openings'] = frappe.db.sql("""select count(*) from `tabJob Opening` \
		where designation=%s and status='Open'
			and company in (select name from tabCompany where lft>=%s and rgt<=%s)
		""", (designation, lft, rgt))[0][0]

	return employee_counts_dict

@frappe.whitelist()
def get_active_staffing_plan_details(company, designation, from_date=getdate(nowdate()), to_date=getdate(nowdate())):
	if not company or not designation:
		frappe.throw(_("Please select Company and Designation"))

	staffing_plan = frappe.db.sql("""
		select sp.name, spd.vacancies, spd.total_estimated_cost
		from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
		where company=%s and spd.designation=%s and sp.docstatus=1
		and to_date >= %s and from_date <= %s """, (company, designation, from_date, to_date), as_dict = 1)

	if not staffing_plan:
		parent_company = frappe.get_cached_value('Company',  company,  "parent_company")
		if parent_company:
			staffing_plan = get_active_staffing_plan_details(parent_company,
				designation, from_date, to_date)

	# Only a single staffing plan can be active for a designation on given date
	return staffing_plan if staffing_plan else None
