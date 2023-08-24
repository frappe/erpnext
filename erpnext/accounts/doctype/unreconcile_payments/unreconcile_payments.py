# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import qb
from frappe.model.document import Document
from frappe.query_builder.functions import Sum

from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries, update_voucher_outstanding


class UnreconcilePayments(Document):
	# def validate(self):
	# 	parent = set([alloc.parent for alloc in self.allocations])
	# 	if len(parent) != 1:
	# 		pass

	@frappe.whitelist()
	def get_allocations_from_payment(self):
		if self.voucher_type == "Payment Entry":
			per = qb.DocType("Payment Entry Reference")
			allocated_references = (
				qb.from_(per)
				.select(
					per.reference_doctype, per.reference_name, Sum(per.allocated_amount).as_("allocated_amount")
				)
				.where((per.docstatus == 1) & (per.parent == self.voucher_no))
				.groupby(per.reference_name)
				.run(as_dict=True)
			)
			return allocated_references

	def add_references(self):
		allocations = self.get_allocations_from_payment()

		for alloc in allocations:
			self.append("allocations", alloc)

	def on_submit(self):
		# todo: add more granular unlinking
		# different amounts for same invoice should be individually unlinkable

		payment_type, paid_from, paid_to, party_type, party = frappe.db.get_all(
			self.voucher_type,
			filters={"name": self.voucher_no},
			fields=["payment_type", "paid_from", "paid_to", "party_type", "party"],
			as_list=1,
		)[0]
		account = paid_from if payment_type == "Receive" else paid_to

		for alloc in self.allocations:
			doc = frappe.get_doc(alloc.reference_doctype, alloc.reference_name)
			unlink_ref_doc_from_payment_entries(doc)
			update_voucher_outstanding(
				alloc.reference_doctype, alloc.reference_name, account, party_type, party
			)
			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", True)
