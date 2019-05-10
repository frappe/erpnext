# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days

class LeaveLedgerEntry(Document):
	pass

def create_leave_ledger_entry(ref_doc, args):
	ledger = dict(
		doctype='Leave Ledger Entry',
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		from_date=ref_doc.from_date,
		transaction_type=ref_doc.doctype,
		transaction_name=ref_doc.name
	)

	ledger.update(args)
	frappe.get_doc(ledger).insert(ignore_permissions=True)