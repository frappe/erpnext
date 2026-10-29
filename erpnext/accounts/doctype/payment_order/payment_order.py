# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.payment_request.payment_request import (
	get_payment_request_status,
	get_requested_amount_in_party_account_currency,
	update_payment_requests_as_per_pe_references,
)
from erpnext.accounts.party import get_party_account


class PaymentOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.payment_order_reference.payment_order_reference import (
			PaymentOrderReference,
		)

		account: DF.Data | None
		amended_from: DF.Link | None
		company: DF.Link
		company_bank: DF.Link | None
		company_bank_account: DF.Link
		naming_series: DF.Literal["PMO-"]
		party: DF.Link | None
		payment_order_type: DF.Literal["", "Payment Request", "Payment Entry"]
		posting_date: DF.Date | None
		references: DF.Table[PaymentOrderReference]
	# end: auto-generated types

	def validate(self):
		self.validate_reference_type()
		self.validate_company_bank_account()
		self.validate_references()
		self.validate_references_not_in_other_orders()

	@property
	def reference_field(self):
		return "payment_request" if self.payment_order_type == "Payment Request" else "reference_name"

	def get_reference_names(self):
		return list({d.get(self.reference_field) for d in self.references if d.get(self.reference_field)})

	def before_mapping(self, source_doc, table_maps):
		self.validate_reference_type(source_doc.doctype)

	def validate_reference_type(self, payment_order_type=None):
		payment_order_type = payment_order_type or self.payment_order_type
		if not payment_order_type:
			return

		for row in self.references:
			if payment_order_type == "Payment Request" and row.payment_request:
				continue
			if (
				payment_order_type == "Payment Entry"
				and row.reference_doctype == "Payment Entry"
				and not row.payment_request
			):
				continue

			frappe.throw(
				_("Row #{0}: Only {1} references are allowed in this Payment Order.").format(
					row.idx, _(payment_order_type)
				)
			)

	def validate_references(self):
		references = self.get_reference_names()
		if not self.payment_order_type or not references:
			return

		reference_details = {
			reference.name: reference
			for reference in frappe.get_all(
				self.payment_order_type,
				filters={"name": ["in", references]},
				fields=["name", "company", "docstatus", "status"],
			)
		}
		for d in self.references:
			self.validate_reference(d, reference_details.get(d.get(self.reference_field)))

	def validate_reference(self, row, reference):
		reference_name = row.get(self.reference_field)
		if not reference or reference.docstatus != 1:
			frappe.throw(
				_("Row #{0}: {1} {2} must be submitted").format(
					row.idx, _(self.payment_order_type), reference_name
				)
			)

		if reference.company != self.company:
			frappe.throw(
				_("Row #{0}: {1} {2} belongs to Company {3}, not {4}").format(
					row.idx, _(self.payment_order_type), reference_name, reference.company, self.company
				)
			)

		if reference.status == "Paid":
			frappe.throw(
				_("Row #{0}: {1} {2} is already paid").format(
					row.idx, _(self.payment_order_type), reference_name
				)
			)

	def validate_references_not_in_other_orders(self):
		references = self.get_reference_names()
		if not self.payment_order_type or not references:
			return

		order = frappe.qb.DocType("Payment Order")
		order_reference = frappe.qb.DocType("Payment Order Reference")
		reference_column = order_reference[self.reference_field]
		other_order = (
			frappe.qb.from_(order_reference)
			.join(order)
			.on(order.name == order_reference.parent)
			.select(reference_column, order.name)
			.where(order.docstatus == 1)
			.where(order.payment_order_type == self.payment_order_type)
			.where(order.name != (self.name or ""))
			.where(reference_column.isin(references))
			.limit(1)
			.run()
		)
		if other_order:
			frappe.throw(
				_("{0} {1} is already in Payment Order {2}").format(
					_(self.payment_order_type), other_order[0][0], other_order[0][1]
				)
			)

	def validate_company_bank_account(self):
		if not self.company_bank_account:
			return

		bank_account = frappe.get_cached_value(
			"Bank Account",
			self.company_bank_account,
			["is_company_account", "company", "disabled", "bank", "account"],
			as_dict=True,
		)
		if not bank_account or bank_account.disabled:
			frappe.throw(_("Bank Account {0} is missing or disabled").format(self.company_bank_account))

		if not bank_account.is_company_account or bank_account.company != self.company:
			frappe.throw(
				_("Bank Account {0} must be a company account belonging to {1}").format(
					self.company_bank_account, self.company
				)
			)

		self.company_bank = bank_account.bank
		self.account = bank_account.account

	def on_submit(self):
		self.update_payment_status()

	def on_cancel(self):
		self.update_payment_status(cancel=True)

	def update_payment_status(self, cancel=False):
		if self.payment_order_type == "Payment Request":
			self.update_payment_request_status(cancel)
			return

		status = "Initiated" if cancel else "Payment Ordered"
		for d in self.references:
			frappe.db.set_value(self.payment_order_type, d.reference_name, "payment_order_status", status)

	def update_payment_request_status(self, cancel=False):
		precision = frappe.get_precision("Payment Request", "outstanding_amount")
		payment_requests = frappe.get_all(
			"Payment Request",
			filters={"name": ["in", self.get_reference_names()]},
			fields=[
				"name",
				"grand_total",
				"outstanding_amount",
				"payment_request_type",
				"currency",
				"party_account_currency",
				"company",
				"reference_doctype",
				"reference_name",
			],
		)

		for payment_request in payment_requests:
			status = "Payment Ordered"
			if cancel:
				status = get_payment_request_status(
					payment_request,
					payment_request.outstanding_amount,
					get_requested_amount_in_party_account_currency(payment_request),
					precision,
				)

			frappe.db.set_value("Payment Request", payment_request.name, "status", status)


def _readable_payment_order(filters: dict) -> str | None:
	"""Authorise the parent before reading its rows.

	A child table carries no permissions of its own, so a read of it has to be authorised on the
	Payment Order the rows belong to.
	"""
	parent = filters.get("parent")
	if not parent or not frappe.db.exists("Payment Order", parent):
		return None

	ptype = "select" if frappe.only_has_select_perm("Payment Order") else "read"
	frappe.has_permission("Payment Order", ptype, doc=parent, throw=True)
	return parent


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mop_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	if not _readable_payment_order(filters):
		return []

	return frappe.get_all(
		"Payment Order Reference",
		filters={"parent": filters.get("parent"), "mode_of_payment": ["like", f"%{txt}%"]},
		fields=["mode_of_payment"],
		limit_start=start,
		limit_page_length=page_len,
		order_by="",  # match the original query (no ORDER BY); avoid get_all's default sort
		as_list=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	if not _readable_payment_order(filters):
		return []

	return frappe.get_all(
		"Payment Order Reference",
		filters={
			"parent": filters.get("parent"),
			"supplier": ["like", f"%{txt}%"],
			"payment_reference": ["is", "not set"],
		},
		fields=["supplier"],
		limit_start=start,
		limit_page_length=page_len,
		order_by="",  # match the original query (no ORDER BY); avoid get_all's default sort
		as_list=True,
	)


@frappe.whitelist(methods=["POST"])
def make_payment_records(name: str, supplier: str, mode_of_payment: str | None = None):
	doc = frappe.get_doc("Payment Order", name)
	doc.check_permission()
	make_journal_entry(doc, supplier, mode_of_payment)


def make_journal_entry(doc, supplier, mode_of_payment=None):
	rows = [
		d
		for d in doc.references
		if d.supplier == supplier
		and not d.payment_reference
		and (not mode_of_payment or mode_of_payment == d.mode_of_payment)
	]
	if not rows:
		frappe.throw(_("Journal Entries are already created for Supplier {0}").format(supplier))

	je = frappe.new_doc("Journal Entry")
	je.company = doc.company
	je.payment_order = doc.name
	je.posting_date = nowdate()
	mode_of_payment_type = frappe._dict(frappe.get_all("Mode of Payment", fields=["name", "type"], as_list=1))

	je.voucher_type = "Bank Entry"
	if mode_of_payment and mode_of_payment_type.get(mode_of_payment) == "Cash":
		je.voucher_type = "Cash Entry"

	party_account = get_party_account("Supplier", supplier, doc.company)
	for d in rows:
		je.append(
			"accounts",
			{
				"account": party_account,
				"debit_in_account_currency": d.amount,
				"party_type": "Supplier",
				"party": supplier,
				"reference_type": d.reference_doctype,
				"reference_name": d.reference_name,
			},
		)

	je.append("accounts", {"account": doc.account, "credit_in_account_currency": sum(d.amount for d in rows)})

	je.flags.ignore_mandatory = True
	je.save()
	set_payment_reference([d.name for d in rows], je.name)
	frappe.msgprint(_("{0} {1} created").format(je.doctype, je.name))


def set_payment_reference(rows: list[str], journal_entry: str):
	order_reference = frappe.qb.DocType("Payment Order Reference")
	frappe.qb.update(order_reference).set(order_reference.payment_reference, journal_entry).where(
		order_reference.name.isin(rows)
	).run()


def clear_payment_reference(journal_entry):
	if not journal_entry.payment_order:
		return

	order_reference = frappe.qb.DocType("Payment Order Reference")
	frappe.qb.update(order_reference).set(order_reference.payment_reference, None).where(
		order_reference.parent == journal_entry.payment_order
	).where(order_reference.payment_reference == journal_entry.name).run()


def update_payment_requests_from_journal_entry(journal_entry, cancel=False):
	if not journal_entry.payment_order:
		return

	references = get_payment_request_allocations(journal_entry)
	update_payment_requests_as_per_pe_references(references, cancel=cancel)

	if cancel:
		for row in references:
			frappe.db.set_value("Payment Request", row.payment_request, "status", "Payment Ordered")
		clear_payment_reference(journal_entry)


def get_payment_request_allocations(journal_entry):
	paid_amounts = defaultdict(float)
	for row in journal_entry.accounts:
		if row.reference_type and row.reference_name:
			paid_amounts[(row.reference_type, row.reference_name)] += flt(row.debit_in_account_currency)

	allocations = []
	for row in frappe.get_all(
		"Payment Order Reference",
		filters={
			"parent": journal_entry.payment_order,
			"parenttype": "Payment Order",
			"payment_reference": journal_entry.name,
			"payment_request": ["is", "set"],
		},
		fields=["payment_request", "amount", "reference_doctype", "reference_name"],
		order_by="idx",
	):
		key = (row.reference_doctype, row.reference_name)
		allocated_amount = min(flt(row.amount), paid_amounts[key])
		paid_amounts[key] -= allocated_amount
		if allocated_amount > 0:
			allocations.append(
				frappe._dict(payment_request=row.payment_request, allocated_amount=allocated_amount)
			)

	return allocations
