# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Abs, Sum
from frappe.utils.data import comma_and

from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	unlink_ref_doc_from_payment_entries,
	update_voucher_outstanding,
)


class UnreconcilePayments(Document):
	def validate(self):
		self.supported_types = ["Payment Entry", "Journal Entry"]
		if not self.voucher_type in self.supported_types:
			frappe.throw(_("Only {0} are supported").format(comma_and(self.supported_types)))

	@frappe.whitelist()
	def get_allocations_from_payment(self):
		allocated_references = []
		ple = qb.DocType("Payment Ledger Entry")
		allocated_references = (
			qb.from_(ple)
			.select(
				ple.account,
				ple.party_type,
				ple.party,
				ple.against_voucher_type.as_("reference_doctype"),
				ple.against_voucher_no.as_("reference_name"),
				Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
				ple.account_currency,
			)
			.where(
				(ple.docstatus == 1)
				& (ple.voucher_type == self.voucher_type)
				& (ple.voucher_no == self.voucher_no)
				& (ple.voucher_no != ple.against_voucher_no)
			)
			.groupby(ple.against_voucher_type, ple.against_voucher_no)
			.run(as_dict=True)
		)

		return allocated_references

	def add_references(self):
		allocations = self.get_allocations_from_payment()

		for alloc in allocations:
			self.append("allocations", alloc)

	def on_submit(self):
		# todo: more granular unreconciliation
		for alloc in self.allocations:
			doc = frappe.get_doc(alloc.reference_doctype, alloc.reference_name)
			unlink_ref_doc_from_payment_entries(doc, self.voucher_no)
			cancel_exchange_gain_loss_journal(doc, self.voucher_type, self.voucher_no)
			update_voucher_outstanding(
				alloc.reference_doctype, alloc.reference_name, alloc.account, alloc.party_type, alloc.party
			)
			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", True)


@frappe.whitelist()
def doc_has_references(doctype: str = None, docname: str = None):
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		return frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "against_voucher_no": docname, "amount": ["<", 0]},
		)
	else:
		return frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "voucher_no": docname, "against_voucher_no": ["!=", docname]},
		)


@frappe.whitelist()
def get_linked_payments_for_doc(
	company: str = None, doctype: str = None, docname: str = None
) -> list:
	if company and doctype and docname:
		_dt = doctype
		_dn = docname
		ple = qb.DocType("Payment Ledger Entry")
		if _dt in ["Sales Invoice", "Purchase Invoice"]:
			criteria = [
				(ple.company == company),
				(ple.delinked == 0),
				(ple.against_voucher_no == _dn),
				(ple.amount < 0),
			]

			res = (
				qb.from_(ple)
				.select(
					ple.company,
					ple.voucher_type,
					ple.voucher_no,
					Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
					ple.account_currency,
				)
				.where(Criterion.all(criteria))
				.groupby(ple.voucher_no, ple.against_voucher_no)
				.having(qb.Field("allocated_amount") > 0)
				.run(as_dict=True)
			)
			return res
		else:
			criteria = [
				(ple.company == company),
				(ple.delinked == 0),
				(ple.voucher_no == _dn),
				(ple.against_voucher_no != _dn),
			]

			query = (
				qb.from_(ple)
				.select(
					ple.company,
					ple.against_voucher_type.as_("voucher_type"),
					ple.against_voucher_no.as_("voucher_no"),
					Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
					ple.account_currency,
				)
				.where(Criterion.all(criteria))
				.groupby(ple.against_voucher_no)
			)
			res = query.run(as_dict=True)
			return res
	return []


@frappe.whitelist()
def create_unreconcile_doc_for_selection(selections=None):
	if selections:
		selections = frappe.json.loads(selections)
		# assuming each row is a unique voucher
		for row in selections:
			unrecon = frappe.new_doc("Unreconcile Payments")
			unrecon.company = row.get("company")
			unrecon.voucher_type = row.get("voucher_type")
			unrecon.voucher_no = row.get("voucher_no")
			unrecon.add_references()

			# remove unselected references
			unrecon.allocations = [
				x
				for x in unrecon.allocations
				if x.reference_doctype == row.get("against_voucher_type")
				and x.reference_name == row.get("against_voucher_no")
			]
			unrecon.save().submit()
