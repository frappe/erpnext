# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days

class LeaveLedgerEntry(Document):
	pass

def create_leave_ledger_entry(ref_doc, args, submit):
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