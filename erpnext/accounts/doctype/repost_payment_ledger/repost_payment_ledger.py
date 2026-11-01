# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn

from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.utils import _delete_adv_pl_entries, _delete_pl_entries, create_payment_ledger_entry

VOUCHER_TYPES = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]


def repost_ple_for_voucher(voucher_type, voucher_no, gle_map=None):
	if voucher_type and voucher_no and gle_map:
		_delete_pl_entries(voucher_type, voucher_no)
		_delete_adv_pl_entries(voucher_type, voucher_no)
		create_payment_ledger_entry(gle_map, cancel=0)


def get_gl_map(doc):
	"""GL map of the voucher as it is posted on submit and on reconciliation"""
	if doc.doctype not in ["Payment Entry", "Journal Entry"]:
		return process_gl_map(doc.get_gl_entries(), merge_entries=False, from_repost=True)

	merge_entries = frappe.get_single_value("Accounts Settings", "merge_similar_account_heads")
	gle_map = process_gl_map(doc.build_gl_map(), merge_entries=merge_entries, from_repost=True)

	if doc.doctype == "Payment Entry":
		# allocation rows of an advance booked in a separate party account
		advance_gl_map = []
		doc.add_advance_gl_entries(advance_gl_map, None)
		gle_map += process_gl_map(advance_gl_map, from_repost=True)

	return gle_map


@frappe.whitelist()
def start_payment_ledger_repost(docname: str | None = None):
	"""
	Repost Payment Ledger Entries for Vouchers through Background Job
	"""
	if docname:
		repost_doc = frappe.get_doc("Repost Payment Ledger", docname)
		repost_doc.check_permission("submit")
		if repost_doc.docstatus.is_submitted() and repost_doc.repost_status in ["Queued", "Failed"]:
			try:
				for entry in repost_doc.repost_vouchers:
					doc = frappe.get_doc(entry.voucher_type, entry.voucher_no)
					# a voucher cancelled after the repost was submitted has no ledger to rebuild
					if doc.docstatus != 1:
						continue

					repost_ple_for_voucher(entry.voucher_type, entry.voucher_no, get_gl_map(doc))

				frappe.db.set_value(repost_doc.doctype, repost_doc.name, "repost_error_log", "")
				frappe.db.set_value(repost_doc.doctype, repost_doc.name, "repost_status", "Completed")
			except Exception:
				frappe.db.rollback()

				traceback = frappe.get_traceback(with_context=True)
				if traceback:
					message = "Traceback: <br>" + traceback
					frappe.db.set_value(repost_doc.doctype, repost_doc.name, "repost_error_log", message)

				frappe.db.set_value(repost_doc.doctype, repost_doc.name, "repost_status", "Failed")


class RepostPaymentLedger(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.repost_payment_ledger_items.repost_payment_ledger_items import (
			RepostPaymentLedgerItems,
		)

		add_manually: DF.Check
		amended_from: DF.Link | None
		company: DF.Link
		posting_date: DF.Date
		repost_error_log: DF.LongText | None
		repost_status: DF.Literal["", "Queued", "Failed", "Completed"]
		repost_vouchers: DF.Table[RepostPaymentLedgerItems]
		voucher_type: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.vouchers = []

	def before_validate(self):
		self.load_vouchers_based_on_filters()
		self.set_status()

	def validate(self):
		self.validate_vouchers()

	def validate_vouchers(self):
		# vouchers loaded from the filters are already submitted vouchers of the company
		if not self.add_manually:
			return

		rows_by_type = {}
		for row in self.repost_vouchers:
			if row.voucher_type not in VOUCHER_TYPES:
				frappe.throw(
					_("Row #{0}: Voucher Type must be one of {1}").format(
						row.idx, ", ".join(_(d) for d in VOUCHER_TYPES)
					)
				)
			rows_by_type.setdefault(row.voucher_type, []).append(row)

		for voucher_type, rows in rows_by_type.items():
			valid_vouchers = frappe.get_all(
				voucher_type,
				filters={
					"name": ["in", [row.voucher_no for row in rows]],
					"docstatus": 1,
					"company": self.company,
				},
				pluck="name",
			)
			for row in rows:
				if row.voucher_no not in valid_vouchers:
					frappe.throw(
						_("Row #{0}: {1} {2} must be submitted and belong to Company {3}").format(
							row.idx,
							_(row.voucher_type),
							frappe.bold(row.voucher_no),
							frappe.bold(self.company),
						)
					)

	def load_vouchers_based_on_filters(self):
		if not self.add_manually:
			self.repost_vouchers.clear()
			self.get_vouchers()
			self.extend("repost_vouchers", copy.deepcopy(self.vouchers))

	def get_vouchers(self):
		self.vouchers.clear()

		filter_on_voucher_types = [self.voucher_type] if self.voucher_type else VOUCHER_TYPES

		for vtype in filter_on_voucher_types:
			doc = qb.DocType(vtype)
			doctype_name = ConstantColumn(vtype)
			query = (
				qb.from_(doc)
				.select(doctype_name.as_("voucher_type"), doc.name.as_("voucher_no"))
				.where(
					(doc.docstatus == 1)
					& (doc.company == self.company)
					& (doc.posting_date.gte(self.posting_date))
				)
			)
			entries = query.run(as_dict=True)
			self.vouchers.extend(entries)

	def set_status(self):
		if self.docstatus == 0:
			self.repost_status = "Queued"

	def on_submit(self):
		execute_repost_payment_ledger(self.name)
		frappe.msgprint(_("Repost started in the background"))


@frappe.whitelist()
def execute_repost_payment_ledger(docname: str):
	"""Repost Payment Ledger Entries by background job."""

	frappe.has_permission("Repost Payment Ledger", ptype="submit", doc=docname, throw=True)

	job_name = "payment_ledger_repost_" + docname

	frappe.enqueue(
		method="erpnext.accounts.doctype.repost_payment_ledger.repost_payment_ledger.start_payment_ledger_repost",
		docname=docname,
		is_async=True,
		job_name=job_name,
	)
