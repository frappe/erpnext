# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
from frappe.utils import add_days

class LeaveLedgerEntry(Document):
	pass

def create_leave_ledger_entry(ref_doc, submit=True):
	ledger = dict(
		doctype='Leave Ledger Entry',
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		from_date=ref_doc.from_date,
		transaction_document_type=ref_doc.doctype,
		transaction_document_name=ref_doc.name
	)

	if ref_doc.carry_forwarded_leaves:
		expiry_days = frappe.db.get_value("Leave Type", ref_doc.leave_type, "carry_forward_leave_expiry")

		ledger.update(dict(
			leaves=ref_doc.carry_forwarded_leaves * 1 if submit else -1,
			to_date=add_days(ref_doc.from_date, expiry_days) if expiry_days else ref_doc.to_date,
			is_carry_forward=1
		))
		frappe.get_doc(ledger).insert()

	ledger.update(dict(
		leaves=ref_doc.new_leaves_allocated * 1 if submit else -1,
		to_date=ref_doc.to_date,
		is_carry_forward=0
	))
	frappe.get_doc(ledger).insert()