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
	get_advance_payment_doctypes,
	unlink_ref_doc_from_payment_entries,
	update_voucher_outstanding,
)


class UnreconcilePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:  # pragma: no cover
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
			.groupby(
				ple.account,
				ple.party_type,
				ple.party,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.account_currency,
			)
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
			if doc.doctype in get_advance_payment_doctypes():
				doc.set_total_advance_paid()

			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", 1 if True else 0)


@frappe.whitelist()
def doc_has_references(doctype: str | None = None, docname: str | None = None):
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
	company: str | None = None, doctype: str | None = None, docname: str | None = None
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
				.groupby(
					ple.voucher_no,
					ple.against_voucher_no,
					ple.company,
					ple.voucher_type,
					ple.account_currency,
				)
				.having(Abs(Sum(ple.amount_in_account_currency)) > 0)
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
				.groupby(ple.against_voucher_no, ple.company, ple.against_voucher_type, ple.account_currency)
			)
			res = query.run(as_dict=True)
			return res
	return []


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


@frappe.whitelist()
def payment_reconciliation_record_on_unreconcile(
	payment_reconciliation_record_name=None, header=None, allocation=None, clearing_date=None
):
	"""
	If `payment_reconciliation_record_name` is provided:
	- Create a duplicate of the given Payment Reconciliation Record with the 'unreconcile' checkbox selected,
	        and update the original record's 'unreconcile' value in the child table only.

	If `payment_reconciliation_record_name` is not provided:
	- Create a new Payment Reconciliation Record using the provided `header` and `allocation`.
	"""
	if payment_reconciliation_record_name:
		# Case when payment_reconciliation_record_name is provided
		original = frappe.get_doc("Payment Reconciliation Record", payment_reconciliation_record_name)
		new_record = frappe.copy_doc(original)
		new_record.flags.ignore_permissions = True
		new_record.unreconcile = 1
		if clearing_date:
			new_record.clearing_date = clearing_date
		filtered_allocations = [alloc for alloc in original.allocation if not alloc.unreconcile]
		new_record.allocation = []
		for alloc in filtered_allocations:
			alloc.unreconcile = 1
			new_record.append("allocation", alloc.as_dict())
		original.flags.ignore_validate_update_after_submit = True
		for allocation in original.allocation:
			allocation.unreconcile = 1
		original.save()
		new_record.save()
		new_record.submit()

	else:
		header = frappe.parse_json(header)
		allocation = frappe.parse_json(allocation)

		# Create a new Payment Reconciliation Record using the provided data
		payment_reconciliation = frappe.new_doc("Payment Reconciliation Record")
		if header.get("clearing_date"):
			payment_reconciliation.clearing_date = header.get("clearing_date")
		payment_reconciliation.company = header.get("company")
		payment_reconciliation.party_type = header.get("party_type")
		payment_reconciliation.party = header.get("party")
		payment_reconciliation.unreconcile = 1  # Set unreconcile flag
		for row in allocation:
			payment_reconciliation.append(
				"allocation",
				{
					"reference_type": row.get("reference_type"),
					"reference_name": row.get("reference_name"),
					"invoice_type": row.get("invoice_type"),
					"invoice_number": row.get("invoice_number"),
					"allocated_amount": row.get("allocated_amount"),
					"unreconcile": 1,
				},
			)
			update_unreconcile_flag(row)
		payment_reconciliation.save()
		payment_reconciliation.submit()


def update_unreconcile_flag(row):
	allocation = frappe.db.get_value(
		"Payment Reconciliation Allocation Records",
		{
			"reference_type": row.get("reference_type"),
			"reference_name": row.get("reference_name"),
			"invoice_type": row.get("invoice_type"),
			"invoice_number": row.get("invoice_number"),
		},
		"name",
	)

	if allocation:
		# Update the `unreconcile` field to 1 for the matched record
		frappe.db.set_value("Payment Reconciliation Allocation Records", allocation, "unreconcile", 1)
