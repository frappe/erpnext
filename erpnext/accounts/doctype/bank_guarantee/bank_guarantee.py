# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


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
def get_voucher_details(bank_guarantee_type, reference_name):
	fields_to_fetch = ["grand_total"]

	doctype = "Sales Order" if bank_guarantee_type == "Receiving" else "Purchase Order"

	if doctype == "Sales Order":
		fields_to_fetch.append("customer")
		fields_to_fetch.append("project")
	else:
		fields_to_fetch.append("supplier")

	bg_doctype = frappe.qb.DocType("Bank Guarantee")

	return frappe.db.get_value(doctype, reference_name, fields_to_fetch, as_dict=True)
