# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Abs, Max, Sum
from frappe.utils.data import comma_and

from erpnext.accounts.utils import (
	unwind_reconciliation,
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
		# todo: more granular unreconciliation
		for alloc in self.allocations:
			doc = frappe.get_doc(alloc.reference_doctype, alloc.reference_name)
			unwind_reconciliation(
				doc,
				payment_name=self.voucher_no,
				referenced_dt=self.voucher_type,
				referenced_dn=self.voucher_no,
			)

			# update outstanding amounts
			update_voucher_outstanding(
				alloc.reference_doctype,
				alloc.reference_name,
				alloc.account,
				alloc.party_type,
				alloc.party,
			)

			frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", 1)


@frappe.whitelist()
def doc_has_references(doctype: str | None = None, docname: str | None = None):
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
		count += len(_linked_bridge_allocations(None, doctype, docname))

	return count


def _linked_bridge_allocations(company: str | None, doctype: str, docname: str) -> list:
	"""Cross-account bridge JEs that REFERENCE (doctype, docname) — returned as
	allocation rows.

	A cross-account reconcile mints a transfer JE (the bridge) and mutates the
	writable side; the other side (a reverse PE, or a non-writable JE) is left
	untouched, so it owns no ledger row pointing at the bridge and the normal forward
	query (`voucher_no == this voucher`) misses it. But the bridge's own PLE carries
	`against_voucher_no = this voucher`, so we walk that link in reverse — the same
	Payment Ledger the rest of this query uses, no JEA join. The `on_submit` unwind
	(`unlink_ref_doc_from_payment_entries` → `remove_ref_doc_link_from_jv`) reverses
	the whole bridge, reopening the counterpart too.

	Mutually exclusive with the normal query: if THIS voucher references the bridge
	(writable side), the bridge does not reference it back, so nothing is returned
	here and no duplicate row is produced.
	"""
	from erpnext.accounts.utils import CROSS_ACCOUNT_BRIDGE_VOUCHER_TYPE

	ple = qb.DocType("Payment Ledger Entry")
	je = qb.DocType("Journal Entry")
	query = (
		qb.from_(ple)
		.inner_join(je)
		.on(je.name == ple.voucher_no)
		.select(
			# grouped by voucher and account; the rest is the same on every row, Max() for strict GROUP BY
			Max(ple.company).as_("company"),
			ple.account,
			Max(ple.party_type).as_("party_type"),
			Max(ple.party).as_("party"),
			Max(ple.voucher_type).as_("reference_doctype"),
			ple.voucher_no.as_("reference_name"),
			Abs(Sum(ple.amount_in_account_currency)).as_("allocated_amount"),
			Max(ple.account_currency).as_("account_currency"),
		)
		.where(
			(ple.against_voucher_no == docname)
			& (ple.voucher_no != docname)
			& (ple.delinked == 0)
			& (je.voucher_type == CROSS_ACCOUNT_BRIDGE_VOUCHER_TYPE)
			& (je.is_system_generated == 1)
		)
		.groupby(ple.voucher_no, ple.account)
	)
	if company:
		query = query.where(ple.company == company)
	return query.run(as_dict=True)


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

			res += _linked_bridge_allocations(company, _dt, _dn)

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
