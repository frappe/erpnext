# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days, today

class LeaveLedgerEntry(Document):
	pass

def create_leave_ledger_entry(ref_doc, args, submit=True):
	ledger = frappe._dict(
		doctype='Leave Ledger Entry',
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		from_date=ref_doc.from_date,
		transaction_type=ref_doc.doctype,
		transaction_name=ref_doc.name
	)
	ledger.update(args)

	if submit:
		frappe.get_doc(ledger).insert(ignore_permissions=True)
	else:
		delete_ledger_entry(ledger)

def delete_ledger_entry(ledger):
	''' Delete ledger entry on cancel of leave application/allocation '''
	ledger_entry, creation_date = frappe.db.get_value("Leave Ledger Entry",
		{'transaction_name': ledger.transaction_name},
		['name', 'creation']
		)

	leave_application_records = []
	if ledger.transaction_type == "Leave Allocation":
		leave_application_records = frappe.get_all("Leave Ledger Entry",
			filters={
				'transaction_type': 'Leave Application',
				'creation_date': (">", creation_date)
			},
			fields=['transaction_type'])
	if not leave_application_records:
		frappe.delete_doc("Leave Ledger Entry", ledger_entry)
	else:
		frappe.throw(_("Leave allocation %s is linked with leave application %s"
			% (ledger_entry, ', '.join(leave_application_records))))

def check_expired_allocation():
	''' Checks for expired allocation by comparing to_date with current_date and
		based on that creates an expiry ledger entry '''
	expired_allocation = frappe.db.get_all("Leave Ledger Allocation",
		filters={
			'to_date': today(),
			'transaction_type': 'Leave Allocation'
		},
		fields=['name', 'transaction_name'])

	if expired_allocation:
		create_expiry_ledger_entry(expired_allocation)

def create_expiry_ledger_entry(expired_allocation):
	for allocation in expired_allocation:
		ledger_entry = frappe.get_doc('Leave Ledger Entry', allocation.name)
		args = {
			'leaves': -ledger_entry.leaves,
			'to_date': '',
			'is_carry_forward': ledger_entry.is_carry_forward
		}
		create_leave_ledger_entry(ledger_entry, args)