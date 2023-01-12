import frappe
from frappe.utils import flt, today
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation, \
	get_allocation_leave_balance_summary, delete_expired_leave_ledger_entry


def execute():
	expired_allocations = frappe.get_all("Leave Allocation", {"to_date": ["<", today()]},
		['name', 'employee', 'from_date', 'to_date', 'leave_type'])

	for allocation_details in expired_allocations:
		leave_balance_summary = get_allocation_leave_balance_summary(allocation_details.name)
		if flt(leave_balance_summary.leave_balance) < 0:
			employee_details = frappe.db.get_value("Employee", allocation_details.employee, ['name', 'employee_name'], as_dict=1)
			print("Employee {0} ({1}) {2} ({3} to {4}) has negative balance after expiry: {5}".format(
				employee_details.employee_name,
				employee_details.name,
				allocation_details.leave_type,
				frappe.format(allocation_details.from_date),
				frappe.format(allocation_details.to_date),
				frappe.format(leave_balance_summary.leave_balance)
			))
			delete_expired_leave_ledger_entry(allocation_details.name)

	process_expired_allocation()
