# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.website.website_generator import WebsiteGenerator
from frappe import _
from erpnext.hr.doctype.staffing_plan.staffing_plan import get_active_staffing_plan_details

class JobOpening(WebsiteGenerator):
	website = frappe._dict(
		template = "templates/generators/job_opening.html",
		condition_field = "publish",
		page_title_field = "job_title",
	)

	def validate(self):
		if not self.route:
			self.route = frappe.scrub(self.job_title).replace('_', '-')
		self.validate_current_vacancies()

	def validate_current_vacancies(self):
		if not self.staffing_plan:
			staffing_plan = get_active_staffing_plan_details(self.company,
				self.designation)
			if staffing_plan:
				self.staffing_plan = staffing_plan[0].name
				self.planned_vacancies = staffing_plan[0].vacancies

		elif not self.planned_vacancies:
			planned_vacancies = frappe.db.sql("""
				select vacancies from `tabStaffing Plan Detail`
				where parent=%s and designation=%s""", (self.staffing_plan, self.designation))
			self.planned_vacancies = planned_vacancies[0][0] if planned_vacancies else None

		if self.staffing_plan:
			staffing_plan_company = frappe.db.get_value("Staffing Plan", self.staffing_plan, "company")
			lft, rgt = frappe.get_cached_value('Company',  staffing_plan_company,  ["lft", "rgt"])
			if not self.planned_vacancies:
				frappe.throw(_("Job Openings for designation {0} already open \
					or hiring completed as per Staffing Plan {1}"
					.format(self.designation, self.staffing_plan)))

	def after_insert(self):
		if self.staffing_plan:
			frappe.db.sql("""update `tabStaffing Plan Detail` 
							 set current_openings = current_openings+1, vacancies = vacancies-1 
							 where parent = %s and designation =%s""",(self.staffing_plan, self.designation))

	def on_trash(self):
		super(JobOpening, self).on_trash()
		if self.staffing_plan:
			frappe.db.sql("""update `tabStaffing Plan Detail` 
							 set current_openings = current_openings-1, vacancies = vacancies+1 
							 where parent = %s and designation =%s""",(self.staffing_plan, self.designation))


	def get_context(self, context):
		context.parents = [{'route': 'jobs', 'title': _('All Jobs') }]

def get_list_context(context):
	context.title = _("Jobs")
	context.introduction = _('Current Job Openings')
