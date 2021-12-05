# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from erpnext.hr.doctype.employee.employee import get_employee_email


class ExitInterview(Document):
	def validate(self):
		self.validate_relieving_date()
		self.set_employee_email()

	def validate_relieving_date(self):
		if not frappe.db.get_value('Employee', self.employee, 'relieving_date'):
			frappe.throw(_('Please set the relieving date for employee {0}').format(
				get_link_to_form('Employee', self.employee)),
				title=_('Relieving Date Missing'))

	def set_employee_email(self):
		employee = frappe.get_doc('Employee', self.employee)
		self.email = get_employee_email(employee)


@frappe.whitelist()
def send_exit_questionnaire(exit_interview):
	exit_interview = frappe.get_doc('Exit Interview', exit_interview)
	context = exit_interview.as_dict()

	employee = frappe.get_doc('Employee', exit_interview.employee)
	context.update(employee.as_dict())

	email = get_employee_email(employee)
	template_name = frappe.db.get_single_value('HR Settings', 'exit_questionnaire_notification_template')
	template = frappe.get_doc('Email Template', template_name)

	if email:
		frappe.sendmail(
			recipients=email,
			subject=template.subject,
			message=frappe.render_template(template.response, context),
			reference_doctype=exit_interview.doctype,
			reference_name=exit_interview.name
		)
		frappe.msgprint(_('Exit Questionnaire sent to {0}').format(email),
			title='Success', indicator='green')
		exit_interview.db_set('questionnaire_email_sent', True)
		exit_interview.notify_update()
	else:
		frappe.msgprint(_('Email IDs for employee not found.'))