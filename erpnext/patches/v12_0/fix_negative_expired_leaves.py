import frappe
from frappe.utils import flt
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation, \
	get_allocation_leave_balance_summary, delete_expired_leave_ledger_entry


def execute():
	expired_allocations = frappe.get_all("Leave Allocation", {"expired": 1})

	for allocation in expired_allocations:
		leave_balance_summary = get_allocation_leave_balance_summary(allocation)
		if not flt(leave_balance_summary.leave_balance):
			delete_expired_leave_ledger_entry(allocation.get('name'))
	
	process_expired_allocation()
