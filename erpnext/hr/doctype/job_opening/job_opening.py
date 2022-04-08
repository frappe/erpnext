# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator

from erpnext.hr.doctype.staffing_plan.staffing_plan import (
	get_active_staffing_plan_details,
	get_designation_counts,
)


class JobOpening(WebsiteGenerator):
	website = frappe._dict(
		template="templates/generators/job_opening.html",
		condition_field="publish",
		page_title_field="job_title",
	)

	def validate(self):
		if not self.route:
			self.route = frappe.scrub(self.job_title).replace("_", "-")
		self.validate_current_vacancies()

	def validate_current_vacancies(self):
		if not self.staffing_plan:
			staffing_plan = get_active_staffing_plan_details(self.company, self.designation)
			if staffing_plan:
				self.staffing_plan = staffing_plan[0].name
				self.planned_vacancies = staffing_plan[0].vacancies
		elif not self.planned_vacancies:
			planned_vacancies = frappe.db.sql(
				"""
				select vacancies from `tabStaffing Plan Detail`
				where parent=%s and designation=%s""",
				(self.staffing_plan, self.designation),
			)
			self.planned_vacancies = planned_vacancies[0][0] if planned_vacancies else None

		if self.staffing_plan and self.planned_vacancies:
			staffing_plan_company = frappe.db.get_value("Staffing Plan", self.staffing_plan, "company")
			lft, rgt = frappe.get_cached_value("Company", staffing_plan_company, ["lft", "rgt"])

			designation_counts = get_designation_counts(self.designation, self.company)
			current_count = designation_counts["employee_count"] + designation_counts["job_openings"]

			if self.planned_vacancies <= current_count:
				frappe.throw(
					_(
						"Job Openings for designation {0} already open or hiring completed as per Staffing Plan {1}"
					).format(self.designation, self.staffing_plan)
				)

	def get_context(self, context):
		context.parents = [{"route": "jobs", "title": _("All Jobs")}]


def get_list_context(context):
	context.title = _("Jobs")
	context.introduction = _("Current Job Openings")
	context.get_list = get_job_openings


def get_job_openings(
	doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by=None
):
	fields = [
		"name",
		"status",
		"job_title",
		"description",
		"publish_salary_range",
		"lower_range",
		"upper_range",
		"currency",
		"job_application_route",
	]

	filters = filters or {}
	filters.update({"status": "Open"})

	if txt:
		filters.update(
			{"job_title": ["like", "%{0}%".format(txt)], "description": ["like", "%{0}%".format(txt)]}
		)

	return frappe.get_all(
		doctype, filters, fields, start=limit_start, page_length=limit_page_length, order_by=order_by
	)
