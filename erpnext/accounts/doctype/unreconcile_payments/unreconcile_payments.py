# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries, update_voucher_outstanding


class UnreconcilePayments(Document):
	def before_save(self):
		if self.voucher_type == "Payment Entry":
			references = frappe.db.get_all(
				"Payment Entry Reference",
				filters={"docstatus": 1, "parent": self.voucher_no},
				fields=["reference_doctype", "reference_name", "allocated_amount"],
			)

			self.set("references", [])
			for ref in references:
				self.append("references", ref)

	def on_submit(self):
		payment_type, paid_from, paid_to, party_type, party = frappe.db.get_all(
			self.voucher_type,
			filters={"name": self.voucher_no},
			fields=["payment_type", "paid_from", "paid_to", "party_type", "party"],
			as_list=1,
		)[0]
		account = paid_from if payment_type == "Receive" else paid_to

		for ref in self.references:
			doc = frappe.get_doc(ref.reference_doctype, ref.reference_name)
			unlink_ref_doc_from_payment_entries(doc)
			update_voucher_outstanding(
				ref.reference_doctype, ref.reference_name, account, party_type, party
			)
			frappe.db.set_value("Unreconcile Payment Entries", ref.name, "unlinked", True)
