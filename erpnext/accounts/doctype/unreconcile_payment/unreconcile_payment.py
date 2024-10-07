# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

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


class UnreconcilePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.unreconcile_payment_entries.unreconcile_payment_entries import (
			UnreconcilePaymentEntries,
		)

		allocations: DF.Table[UnreconcilePaymentEntries]
		amended_from: DF.Link | None
		company: DF.Link | None
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.supported_types = ["Payment Entry", "Journal Entry"]
		if self.voucher_type not in self.supported_types:
			frappe.throw(_("Only {0} are supported").format(comma_and(self.supported_types)))

	@frappe.whitelist()
	def get_allocations_from_payment(self):
		allocated_references = []

		advance_doctypes = frappe.get_hooks("advance_payment_payable_doctypes") + frappe.get_hooks(
			"advance_payment_receivable_doctypes"
		)

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

		if self.voucher_type == "Payment Entry":
			res = frappe.db.get_all(
				"Payment Entry Reference",
				filters={
					"docstatus": 1,
					"parent": self.voucher_no,
					"reference_doctype": ["in", advance_doctypes],
				},
				fields=["reference_doctype", "reference_name", "allocated_amount"],
			)
			allocated_references += res

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
			if doc.doctype in frappe.get_hooks("advance_payment_payable_doctypes") + frappe.get_hooks(
				"advance_payment_receivable_doctypes"
			):
				doc.set_total_advance_paid()

			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", True)


@frappe.whitelist()
def doc_has_references(doctype: str | None = None, docname: str | None = None):
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		return frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "against_voucher_no": docname, "amount": ["<", 0]},
		)
	else:
		# For Backwards compatibility, check ledger as well.
		# On Old PLE records, this can lead to double counting. Thats fine.
		# As we are not looking for exact count
		ledger_references = frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "voucher_no": docname, "against_voucher_no": ["!=", docname]},
		)

		advance_doctypes = frappe.get_hooks("advance_payment_payable_doctypes") + frappe.get_hooks(
			"advance_payment_receivable_doctypes"
		)
		pe_references = len(
			frappe.db.get_all(
				"Payment Entry Reference",
				filters={
					"docstatus": 1,
					"parent": docname,
					"reference_doctype": ["in", advance_doctypes],
				},
			)
		)
		return ledger_references + pe_references


def get_linked_payments_for_invoices(
	company: str | None = None, doctype: str | None = None, docname: str | None = None
) -> list:
	res = []
	if company and doctype and docname:
		ple = qb.DocType("Payment Ledger Entry")
		if doctype in ["Sales Invoice", "Purchase Invoice"]:
			criteria = [
				(ple.company == company),
				(ple.delinked == 0),
				(ple.against_voucher_no == docname),
				(ple.amount < 0),
			]
			res.extend(
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


def get_linked_docs_for_payments(
	company: str | None = None, doctype: str | None = None, docname: str | None = None
) -> list:
	res = []
	if company and doctype and docname:
		ple = qb.DocType("Payment Ledger Entry")
		criteria = [
			(ple.company == company),
			(ple.delinked == 0),
			(ple.voucher_no == docname),
			(ple.against_voucher_no != docname),
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
		res.extend(query.run(as_dict=True))

		# TODO: handle duplicates due to Old payments storing SO/PO references in Ledger
		advance_doctypes = frappe.get_hooks("advance_payment_payable_doctypes") + frappe.get_hooks(
			"advance_payment_receivable_doctypes"
		)
		pe = qb.DocType("Payment Entry Reference")
		pe_references = (
			qb.from_(pe)
			.select(
				pe.reference_doctype.as_("voucher_type"),
				pe.reference_name.as_("voucher_no"),
				pe.allocated_amount,
			)
			.where(pe.docstatus.eq(1) & pe.parent.eq(docname) & pe.reference_doctype.isin(advance_doctypes))
			.run(as_dict=True)
		)
		res.extend(pe_references)
	return res


@frappe.whitelist()
def get_linked_payments_for_doc(
	company: str | None = None, doctype: str | None = None, docname: str | None = None
) -> list:
	references = []
	if company and doctype and docname:
		get_linked_payments_for_invoices(company, doctype, docname)
		if doctype in ["Sales Invoice", "Purchase Invoice"]:
			references.extend(get_linked_payments_for_invoices(company, doctype, docname))
		else:
			references.extend(get_linked_docs_for_payments(company, doctype, docname))
	return references


@frappe.whitelist()
def create_unreconcile_doc_for_selection(selections=None):
	if selections:
		selections = json.loads(selections)
		# assuming each row is a unique voucher
		for row in selections:
			unrecon = frappe.new_doc("Unreconcile Payment")
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
