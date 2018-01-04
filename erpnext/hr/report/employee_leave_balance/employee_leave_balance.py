# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_allocation_records, get_leave_balance_on, get_approved_leaves_for_period


def execute(filters=None):
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")
	
	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)
	
	return columns, data
	
def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link/Employee:150", 
		_("Employee Name") + "::200", 
		_("Department") +"::150"
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Taken") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Balance") + ":Float:160")
	
	return columns
	
def get_data(filters, leave_types):
	user = frappe.session.user
	allocation_records_based_on_to_date = get_leave_allocation_records(filters.to_date)

	active_employees = frappe.get_all("Employee", 
		filters = { "status": "Active", "company": filters.company}, 
		fields = ["name", "employee_name", "department", "user_id"])
	
	data = []
	for employee in active_employees:
		leave_approvers = [l.leave_approver for l in frappe.db.sql("""select leave_approver from `tabEmployee Leave Approver` where parent = %s""",
							(employee.name),as_dict=True)]
		if (len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
			row = [employee.name, employee.employee_name, employee.department]

			for leave_type in leave_types:
				# leaves taken
				leaves_taken = get_approved_leaves_for_period(employee.name, leave_type,
					filters.from_date, filters.to_date)
	
				# closing balance
				closing = get_leave_balance_on(employee.name, leave_type, filters.to_date,
					allocation_records_based_on_to_date.get(employee.name, frappe._dict()))

				row += [leaves_taken, closing]
			
			data.append(row)
		
	return data