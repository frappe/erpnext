from __future__ import unicode_literals

import frappe
from frappe import _

def execute():
	if not frappe.db.exists('Salary Component', _('Overtime Allowance')):
		frappe.get_doc({'doctype': 'Salary Component',
		'salary_component': _('Overtime Allowance'),
		'description': _('Overtime Allowance'),
		'type': 'Earning'}).insert()

	frappe.db.set_value('Payroll Settings', None, 'overtime_salary_component', _('Overtime Allowance'))

	frappe.db.sql('UPDATE `tabAttendance` SET working_time = working_hours * 3600 ;')