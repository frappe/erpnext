# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _

class BankGuarantee(Document):
	def validate(self):
		if not (self.customer or self.supplier):
			frappe.throw(_("Select the customer or supplier."))

	def on_submit(self):
		if not self.bank_guarantee_number:
			frappe.throw(_("Enter the Bank Guarantee Number before submittting."))
		if not self.name_of_beneficiary:
			frappe.throw(_("Enter the name of the Beneficiary before submittting."))
		if not self.bank:
			frappe.throw(_("Enter the name of the bank or lending institution before submittting."))

@frappe.whitelist()
def get_vouchar_detials(column_list, doctype, docname):
	print (column_list, doctype, docname)
	return frappe.db.sql(''' select {columns} from `tab{doctype}` where name=%s'''
		.format(columns=", ".join(json.loads(column_list)), doctype=doctype), docname, as_dict=1)[0]

