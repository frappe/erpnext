# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days, today

class LeaveLedgerEntry(Document):
	def validate_entries(self):
		leave_records = frappe.get_all('Leave Ledger Entry', ['leaves'])
		if sum(record.get("leaves") for record in leave_records) <0:
			frappe.throw(_("Invalid Ledger Entry"))

def create_leave_ledger_entry(ref_doc, args, submit=True):
	ledger = frappe._dict(
		doctype='Leave Ledger Entry',
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		transaction_type=ref_doc.doctype,
		transaction_name=ref_doc.name,
	)
	ledger.update(args)
	if submit:
		frappe.get_doc(ledger).submit()
	else:
		delete_ledger_entry(ledger)

def delete_ledger_entry(ledger):
	''' Delete ledger entry on cancel of leave application/allocation/encashment '''

	leave_application_records = []
	# prevent deletion when leave application has been created after allocation
	if ledger.transaction_type == "Leave Allocation":
		leave_application_records = frappe.get_all("Leave Ledger Entry",
			filters={
				'employee': ledger.employee,
				'leave_type': ledger.leave_type,
				'transaction_type': 'Leave Application',
				'from_date': (">=", ledger.from_date),
				'to_date': ('<=', ledger.to_date)
			},
			fields=['transaction_name'])

	if not leave_application_records:
		frappe.db.sql("""DELETE
			FROM `tabLeave Ledger Entry`
			WHERE
				`transaction_name`=%s""", (ledger.transaction_name))
	else:
		frappe.throw(_("Leave allocation %s is linked with leave application %s"
			% (ledger_entry, ', '.join(leave_application_records))))

def check_expired_allocation():
	''' Checks for expired allocation by comparing to_date with current_date and
		based on that creates an expiry ledger entry '''
	expired_allocation = frappe.get_all("Leave Ledger Allocation",
		filters={
			'to_date': today(),
			'transaction_type': 'Leave Allocation'
		},
		fields=['*'])

	if expired_allocation:
		create_expiry_ledger_entry(expired_allocation)

def create_expiry_ledger_entry(expired_allocation):
	for allocation in expired_allocation:
		filters = {
				'employee': allocation.employee,
				'leave_type': allocation.leave_type,
				'from_date': ('>=', allocation.from_date),
			}
		# get only application ledger entries in case of carry forward
		if allocation.is_carry_forward:
			filters.update(dict(transaction_type='Leave Application'))

		leave_records = frappe.get_all("Leave Ledger Entry",
			filters=filters,
			fields=['leaves'])

		leaves = sum(record.get("leaves") for record in leave_records)

		if allocation.is_carry_forward:
			leaves = allocation.leaves + leaves

		if leaves > 0:
			args = frappe._dict(
				leaves=allocation.leaves * -1,
				to_date='',
				is_carry_forward=allocation.is_carry_forward,
				is_expired=1,
				from_date=allocation.to_date
			)
			create_leave_ledger_entry(allocation, args)