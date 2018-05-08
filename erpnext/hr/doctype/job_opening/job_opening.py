# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.website.website_generator import WebsiteGenerator
from frappe import _
from erpnext.hr.doctype.staffing_plan.staffing_plan import get_current_employee_count, get_active_staffing_plan_and_vacancies

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
			vacancies = get_active_staffing_plan_and_vacancies(self.company,
				self.designation, self.department)
			if vacancies:
				self.staffing_plan = vacancies[0]
				self.planned_vacancies = vacancies[1]
		elif not self.planned_vacancies:
			planned_vacancies = frappe.db.sql("""
				select vacancies from `tabStaffing Plan Detail`
				where parent=%s and designation=%s""", (self.staffing_plan, self.designation))
			self.planned_vacancies = planned_vacancies[0][0] if planned_vacancies else None

		if self.staffing_plan and self.planned_vacancies:
			staffing_plan_company = frappe.db.get_value("Staffing Plan", self.staffing_plan, "company")
			lft, rgt = frappe.db.get_value("Company", staffing_plan_company, ["lft", "rgt"])

			current_count = get_current_employee_count(self.designation, staffing_plan_company)
			current_count+= frappe.db.sql("""select count(*) from `tabJob Opening` \
				where designation=%s and status='Open'
					and company in (select name from tabCompany where lft>=%s and rgt<=%s)
				""", (self.designation, lft, rgt))[0][0]

			if self.planned_vacancies <= current_count:
				frappe.throw(_("Job Openings for designation {0} and company {1} already opened or hiring completed as per Staffing Plan {2}".format(self.designation, staffing_plan_company, self.staffing_plan)))

	def get_context(self, context):
		context.parents = [{'route': 'jobs', 'title': _('All Jobs') }]

def get_list_context(context):
	context.title = _("Jobs")
	context.introduction = _('Current Job Openings')
