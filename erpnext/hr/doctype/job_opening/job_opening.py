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

		if self.staffing_plan:
			self.validate_current_vacancies()

	def validate_current_vacancies(self):
		current_count = get_current_employee_count(self.designation)
		current_count+= frappe.db.sql("""select count(*) from `tabJob Opening` \
						where designation = '{0}' and status='Open'""".format(self.designation))[0][0]

		vacancies = get_active_staffing_plan_and_vacancies(self.company, self.designation, self.department)[1]
		# set staffing_plan too?
		if vacancies and vacancies <= current_count:
			frappe.throw(_("Job Openings for designation {0} already opened or hiring \
						completed as per Staffing Plan {1}".format(self.designation, self.staffing_plan)))

	def get_context(self, context):
		context.parents = [{'route': 'jobs', 'title': _('All Jobs') }]

def get_list_context(context):
	context.title = _("Jobs")
	context.introduction = _('Current Job Openings')
