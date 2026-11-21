# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Abs, Max, Sum
from frappe.utils import cstr, flt
from frappe.utils.data import comma_and

from erpnext import _refuse
from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	get_linked_exchange_gain_loss_journal,
	unlink_ref_doc_from_payment_entries,
	update_voucher_outstanding,
)

UNRECONCILABLE_DOCTYPES = ("Payment Entry", "Journal Entry")


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
		self.supported_types = list(UNRECONCILABLE_DOCTYPES)
		if self.voucher_type not in self.supported_types:
			frappe.throw(_("Only {0} are supported").format(comma_and(self.supported_types)))

	@frappe.whitelist()
	def get_allocations_from_payment(self):
		return get_linked_payments_for_doc(
			company=self.company,
			doctype=self.voucher_type,
			docname=self.voucher_no,
		)

	def add_references(self):
		allocations = self.get_allocations_from_payment()

		for alloc in allocations:
			self.append("allocations", alloc)

	def on_submit(self):
		self.cancel_legacy_return_exchange_journal()
		# todo: more granular unreconciliation
		for alloc in self.allocations:
			doc = frappe.get_doc(alloc.reference_doctype, alloc.reference_name)
			unlink_ref_doc_from_payment_entries(doc, self.voucher_no)
			cancel_exchange_gain_loss_journal(doc, self.voucher_type, self.voucher_no)

			# update outstanding amounts
			update_voucher_outstanding(
				alloc.reference_doctype,
				alloc.reference_name,
				alloc.account,
				alloc.party_type,
				alloc.party,
				update_payment_schedule=True,
			)

			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", 1)

	def cancel_legacy_return_exchange_journal(self):
		if self.voucher_type != "Journal Entry":
			return

		journal = frappe.get_doc("Journal Entry", self.voucher_no)
		if not (
			journal.docstatus == 1
			and journal.is_system_generated
			and journal.voucher_type in ("Credit Note", "Debit Note")
			and len(journal.accounts) == 2
		):
			return

		journal.check_permission("write")
		return_rows = [
			row
			for row in journal.accounts
			if row.reference_type in ("Sales Invoice", "Purchase Invoice")
			and row.reference_name
			and frappe.get_cached_value(row.reference_type, row.reference_name, "is_return")
		]
		if len(return_rows) != 1:
			return

		return_row = return_rows[0]
		invoice_row = next(row for row in journal.accounts if row.name != return_row.name)
		if not any(
			row.reference_doctype == return_row.reference_type
			and row.reference_name == return_row.reference_name
			for row in self.allocations
		):
			return

		legacy_journals = self.get_legacy_return_exchange_journals(journal, invoice_row, return_row)
		if not legacy_journals:
			return

		self.validate_legacy_return_exchange_journal(journal, invoice_row, return_row, legacy_journals)
		gain_loss = legacy_journals[0]
		precision = gain_loss.precision("total_debit")
		amount = return_row.debit_in_account_currency - return_row.credit_in_account_currency
		return_rate = frappe.get_cached_value(
			return_row.reference_type, return_row.reference_name, "conversion_rate"
		)
		difference = flt(amount * return_rate, precision) - flt(amount * return_row.exchange_rate, precision)
		if gain_loss.creation < journal.creation or flt(
			sum(row.debit - row.credit for row in gain_loss.accounts if row.account == return_row.account)
			- difference,
			precision,
		):
			frappe.throw(
				_("Exchange journal {0} could not be matched to reconciliation journal {1}.").format(
					frappe.bold(gain_loss.name), frappe.bold(journal.name)
				),
				title=_("Exchange Journal Mismatch"),
			)

		gain_loss.cancel()

	def get_legacy_return_exchange_journals(self, journal, invoice_row, return_row):
		legacy_journals = []
		for name in get_linked_exchange_gain_loss_journal(
			return_row.reference_type, return_row.reference_name, 1
		):
			gain_loss = frappe.get_doc("Journal Entry", name)
			if any(
				row.reference_type == "Journal Entry" and row.reference_name == journal.name
				for row in gain_loss.accounts
			):
				return []

			if len(gain_loss.accounts) != 2 or gain_loss.company != journal.company:
				continue

			party_rows = gain_loss.get("accounts", {"account": return_row.account})
			if len(party_rows) != 1:
				continue

			party_row = party_rows[0]
			reference_row = next(row for row in gain_loss.accounts if row.name != party_row.name)
			if (
				party_row.reference_type == return_row.reference_type
				and party_row.reference_name == return_row.reference_name
				and party_row.party_type == return_row.party_type
				and party_row.party == return_row.party
				and reference_row.reference_type == return_row.reference_type
				and (
					not invoice_row.reference_name
					or reference_row.reference_name == invoice_row.reference_name
				)
			):
				legacy_journals.append(gain_loss)

		return legacy_journals

	def validate_legacy_return_exchange_journal(self, journal, invoice_row, return_row, legacy_journals):
		# Old exchange journals identify the invoice pair, not the individual reconciliation.
		linked_journals = frappe.get_all(
			"Journal Entry Account",
			filters={
				"reference_type": return_row.reference_type,
				"reference_name": return_row.reference_name,
				"docstatus": 1,
			},
			pluck="parent",
		)
		if invoice_row.reference_name:
			linked_journals = frappe.get_all(
				"Journal Entry Account",
				filters={
					"parent": ("in", linked_journals),
					"reference_type": invoice_row.reference_type,
					"reference_name": invoice_row.reference_name,
					"docstatus": 1,
				},
				pluck="parent",
			)

		linked_journals = frappe.get_all(
			"Journal Entry",
			filters={
				"name": ("in", linked_journals),
				"company": journal.company,
				"voucher_type": journal.voucher_type,
				"is_system_generated": 1,
				"docstatus": 1,
			},
			pluck="name",
		)
		if len(legacy_journals) != 1 or linked_journals != [journal.name]:
			frappe.throw(
				_(
					"Cannot uniquely match exchange journals {0} to {1}. Review and cancel the matching exchange journal and reconciliation journal instead."
				).format(
					comma_and([frappe.bold(row.name) for row in legacy_journals]), frappe.bold(journal.name)
				),
				title=_("Ambiguous Exchange Journal"),
			)


@frappe.whitelist()
def doc_has_references(doctype: str | None = None, docname: str | None = None):
	if not doctype or not docname:
		frappe.throw(_("{0} and {1} are required").format(frappe.bold("doctype"), frappe.bold("docname")))
	frappe.has_permission(doctype, "read", doc=docname, throw=True)

	count = 0
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		count = frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "against_voucher_no": docname, "amount": ["<", 0]},
		)
	else:
		count = frappe.db.count(
			"Payment Ledger Entry",
			filters={"delinked": 0, "voucher_no": docname, "against_voucher_no": ["!=", docname]},
		)
		count += frappe.db.count(
			"Advance Payment Ledger Entry",
			filters={
				"delinked": 0,
				"voucher_no": docname,
				"voucher_type": doctype,
				"event": ["=", "Submit"],
			},
		)

	return count


@frappe.whitelist()
def get_linked_payments_for_doc(
	company: str | None = None, doctype: str | None = None, docname: str | None = None
) -> list:
	if company and doctype and docname:
		frappe.has_permission(doctype, doc=docname, throw=True)

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
					Max(ple.account).as_("account"),
					Max(ple.party_type).as_("party_type"),
					Max(ple.party).as_("party"),
					Max(ple.company).as_("company"),
					Max(ple.voucher_type).as_("reference_doctype"),
					ple.voucher_no.as_("reference_name"),
					Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
					Max(ple.account_currency).as_("account_currency"),
				)
				.where(Criterion.all(criteria))
				.groupby(ple.voucher_no, ple.against_voucher_no)
				.having(Abs(Sum(ple.amount_in_account_currency)) > 0)
				# deterministic order across backends (postgres GROUP BY does not imply ordering)
				.orderby(ple.voucher_no)
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
					Max(ple.company).as_("company"),
					Max(ple.account).as_("account"),
					Max(ple.party_type).as_("party_type"),
					Max(ple.party).as_("party"),
					Max(ple.against_voucher_type).as_("reference_doctype"),
					ple.against_voucher_no.as_("reference_name"),
					Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
					Max(ple.account_currency).as_("account_currency"),
				)
				.where(Criterion.all(criteria))
				.groupby(ple.against_voucher_no)
				# deterministic order across backends (postgres GROUP BY does not imply ordering)
				.orderby(ple.against_voucher_no)
			)

			res = query.run(as_dict=True)

			res += get_linked_advances(company, _dn)

			return res

	return []


def get_linked_advances(company, docname):
	adv = qb.DocType("Advance Payment Ledger Entry")
	criteria = [
		(adv.company == company),
		(adv.delinked == 0),
		(adv.voucher_no == docname),
		(adv.event == "Submit"),
	]

	return (
		qb.from_(adv)
		.select(
			# non-grouped columns are constant per against_voucher_no -> Max() is unchanged and postgres-valid
			Max(adv.company).as_("company"),
			Max(adv.against_voucher_type).as_("reference_doctype"),
			adv.against_voucher_no.as_("reference_name"),
			Abs(Sum(adv.amount)).as_("allocated_amount"),
			Max(adv.currency).as_("currency"),
		)
		.where(Criterion.all(criteria))
		.having(Abs(Sum(adv.amount)) > 0)
		.groupby(adv.against_voucher_no)
		# deterministic order across backends (postgres GROUP BY does not imply ordering)
		.orderby(adv.against_voucher_no)
		.run(as_dict=True)
	)


@frappe.whitelist()
def create_unreconcile_doc_for_selection(selections: str | list | None = None):
	if selections:
		selections = frappe.parse_json(selections)
		for row in selections:
			voucher_type = row.get("voucher_type")
			if voucher_type not in UNRECONCILABLE_DOCTYPES:
				frappe.throw(_("Only {0} are supported").format(comma_and(list(UNRECONCILABLE_DOCTYPES))))
			row["voucher_no"] = cstr(row.get("voucher_no"))
			if not row["voucher_no"] or not frappe.has_permission(
				voucher_type, "write", doc=row["voucher_no"]
			):
				_refuse()

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
