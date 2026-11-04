# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

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
		self.validate_company_bank_account()
		self.validate_references()
		self.validate_references_not_in_other_orders()

	@property
	def reference_field(self):
		return "payment_request" if self.payment_order_type == "Payment Request" else "reference_name"

	def get_reference_names(self):
		return list({d.get(self.reference_field) for d in self.references if d.get(self.reference_field)})

	def validate_references(self):
		references = self.get_reference_names()
		if not self.payment_order_type or not references:
			return

		order_status_field = (
			"status" if self.payment_order_type == "Payment Request" else "payment_order_status"
		)
		reference_details = {
			reference.name: reference
			for reference in frappe.qb.get_query(
				self.payment_order_type,
				fields=["name", "company", "docstatus", f"{order_status_field} as order_status"],
				filters={"name": ["in", references]},
				for_update=self.docstatus == 1,
			).run(as_dict=True)
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

		if reference.company and reference.company != self.company:
			frappe.throw(
				_("Row #{0}: {1} {2} belongs to Company {3}, not {4}").format(
					row.idx, _(self.payment_order_type), reference_name, reference.company, self.company
				)
			)

		if self.docstatus == 1 and reference.order_status == "Payment Ordered":
			frappe.throw(
				_("Row #{0}: {1} {2} is already in another Payment Order").format(
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
		status = "Payment Ordered"
		if cancel:
			status = "Initiated"

		if self.payment_order_type == "Payment Request":
			ref_field = "status"
			ref_doc_field = frappe.scrub(self.payment_order_type)
		else:
			ref_field = "payment_order_status"
			ref_doc_field = "reference_name"

		for d in self.references:
			frappe.db.set_value(self.payment_order_type, d.get(ref_doc_field), ref_field, status)


def _readable_payment_order(filters):
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
def get_mop_query(doctype, txt, searchfield, start, page_len, filters):
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
def get_supplier_query(doctype, txt, searchfield, start, page_len, filters):
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


@frappe.whitelist()
def make_payment_records(name, supplier, mode_of_payment=None):
	doc = frappe.get_doc("Payment Order", name)
	doc.check_permission()
	make_journal_entry(doc, supplier, mode_of_payment)


def make_journal_entry(doc, supplier, mode_of_payment=None):
	je = frappe.new_doc("Journal Entry")
	je.company = doc.company
	je.payment_order = doc.name
	je.posting_date = nowdate()
	mode_of_payment_type = frappe._dict(frappe.get_all("Mode of Payment", fields=["name", "type"], as_list=1))

	je.voucher_type = "Bank Entry"
	if mode_of_payment and mode_of_payment_type.get(mode_of_payment) == "Cash":
		je.voucher_type = "Cash Entry"

	paid_amt = 0
	party_account = get_party_account("Supplier", supplier, doc.company)
	for d in doc.references:
		if d.supplier == supplier and (not mode_of_payment or mode_of_payment == d.mode_of_payment):
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

			paid_amt += d.amount

	je.append("accounts", {"account": doc.account, "credit_in_account_currency": paid_amt})

	je.flags.ignore_mandatory = True
	je.save()
	frappe.msgprint(_("{0} {1} created").format(je.doctype, je.name))
