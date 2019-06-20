# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days, today, flt, DATE_FORMAT

class LeaveLedgerEntry(Document):
	def on_cancel(self):
		# allow cancellation of expiry leaves
		if not self.is_expired:
			frappe.throw(_("Only expired allocation can be cancelled"))

def validate_leave_allocation_against_leave_application(ledger):
	''' Checks that leave allocation has no leave application against it '''
	leave_application_records = frappe.get_all("Leave Ledger Entry",
		filters={
			'employee': ledger.employee,
			'leave_type': ledger.leave_type,
			'transaction_type': 'Leave Application',
			'from_date': (">=", ledger.from_date),
			'to_date': ('<=', ledger.to_date)
		}, fields=['transaction_name'])

	if leave_application_records:
		frappe.throw(_("Leave allocation %s is linked with leave application %s"
			% (ledger.transaction_name, ', '.join(leave_application_records))))

def create_leave_ledger_entry(ref_doc, args, submit=True):
	ledger = frappe._dict(
		doctype='Leave Ledger Entry',
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		transaction_type=ref_doc.doctype,
		transaction_name=ref_doc.name,
		is_carry_forward=0,
		is_expired=0,
		is_lwp=0
	)
	ledger.update(args)
	if submit:
		frappe.get_doc(ledger).submit()
	else:
		delete_ledger_entry(ledger)

def delete_ledger_entry(ledger):
	''' Delete ledger entry on cancel of leave application/allocation/encashment '''
	if ledger.transaction_type == "Leave Allocation":
		validate_leave_allocation_against_leave_application(ledger)

	expired_entry = get_previous_expiry_ledger_entry(ledger)
	frappe.db.sql("""DELETE
		FROM `tabLeave Ledger Entry`
		WHERE
			`transaction_name`=%s
			OR `name`=%s""", (ledger.transaction_name, expired_entry))

def get_previous_expiry_ledger_entry(ledger):
	''' Returns the expiry ledger entry having same creation date as the ledger entry to be cancelled '''
	creation_date = frappe.db.get_value("Leave Ledger Entry", filters={
			'transaction_name': ledger.transaction_name,
			'is_expired': 0
		}, fieldname=['creation']).strftime(DATE_FORMAT)

	return frappe.db.get_value("Leave Ledger Entry", filters={
		'creation': ('like', creation_date+"%"),
		'employee': ledger.employee,
		'leave_type': ledger.leave_type,
		'is_expired': 1,
		'docstatus': 1,
		'is_carry_forward': 0
	}, fieldname=['name'])

def process_expired_allocation():
	''' Check if a carry forwarded allocation has expired and create a expiry ledger entry '''

	# fetch leave type records that has carry forwarded leaves expiry
	leave_type_records = frappe.db.get_values("Leave Type", filters={
			'carry_forward_leave_expiry': (">", 0)
		}, fieldname=['name'])

	if leave_type_records:
		leave_type = [record[0] for record in leave_type_records]
		expired_allocation = frappe.get_all("Leave Ledger Entry",
			filters={
				'to_date': add_days(today(), -1),
				'transaction_type': 'Leave Allocation',
				'is_carry_forward': 1,
				'leave_type': ('in', leave_type)
			}, fields=['leaves', 'to_date', 'employee', 'leave_type'])

	if expired_allocation:
		create_expiry_ledger_entry(expired_allocation)

def create_expiry_ledger_entry(expired_allocation):
	''' Create expiry ledger entry for carry forwarded leaves '''
	for allocation in expired_allocation:

		leaves_taken = get_leaves_taken(allocation)
		leaves = flt(allocation.leaves) + flt(leaves_taken)

		if leaves > 0:
			args = frappe._dict(
				leaves=allocation.leaves * -1,
				to_date=allocation.to_date,
				is_carry_forward=1,
				is_expired=1,
				from_date=allocation.to_date
			)
			create_leave_ledger_entry(allocation, args)

def get_leaves_taken(allocation):
	return frappe.db.get_value("Leave Ledger Entry",
		filters={
			'employee': allocation.employee,
			'leave_type': allocation.leave_type,
			'from_date': ('>=', allocation.from_date),
			'to_date': ('<=', allocation.to_date),
			'transaction_type': 'Leave application'
		}, fieldname=['SUM(leaves)'])