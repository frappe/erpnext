# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, flt, cint

class ChequeLot(Document):
	pass
def update_cheque_lot(ref_doc):
	if ref_doc:
		current = ref_doc.next_no
		if cint(current) < cint(ref_doc.end_no):
			ref_doc.db_set("next_no", str((cint(current) + 1)).zfill(len(ref_doc.next_no)))
			ref_doc.db_set("status", "In Use")
		else:
			ref_doc.db_set("status", "Used")

def get_cheque_info(name=None):
	res = []
	if name:
		ref_doc = frappe.get_doc("Cheque Lot", name)
		cheque_no = ref_doc.next_no
		cheque_date = nowdate()
		res.append({"reference_no": cheque_no})
		res.append({"reference_date": cheque_date})
		update_cheque_lot(ref_doc)
	
	return res

@frappe.whitelist()
def get_cheque_no_and_date(name=None):
	return get_cheque_info(name) 