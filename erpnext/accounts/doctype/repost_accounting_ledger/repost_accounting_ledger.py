# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import inspect

import frappe
from frappe import _, qb
from frappe.desk.form.linked_with import get_child_tables_of_doctypes
from frappe.model.document import Document
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.data import comma_and


class RepostAccountingLedger(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.repost_accounting_ledger_items.repost_accounting_ledger_items import (
			RepostAccountingLedgerItems,
		)

		amended_from: DF.Link | None
		company: DF.Link | None
		delete_cancelled_entries: DF.Check
		error_log: DF.Code | None
		scheduled_job: DF.Link | None
		status: DF.Literal[
			"", "Queued", "In Progress", "Partially Reposted", "Completed", "Failed", "Cancelled"
		]
		vouchers: DF.Table[RepostAccountingLedgerItems]
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._allowed_types = get_allowed_types_from_settings()

	def validate(self):
		self.validate_vouchers()
		self.validate_for_closed_fiscal_year()
		self.validate_for_deferred_accounting()

	def validate_for_deferred_accounting(self):
		sales_docs = [x.voucher_no for x in self.vouchers if x.voucher_type == "Sales Invoice"]
		purchase_docs = [x.voucher_no for x in self.vouchers if x.voucher_type == "Purchase Invoice"]
		validate_docs_for_deferred_accounting(sales_docs, purchase_docs)

	def validate_for_closed_fiscal_year(self):
		if self.vouchers:
			latest_pcv = (
				frappe.db.get_all(
					"Period Closing Voucher",
					filters={"company": self.company, "docstatus": 1},
					order_by="period_end_date desc",
					pluck="period_end_date",
					limit=1,
				)
				or None
			)
			if not latest_pcv:
				return

			for vtype in self._allowed_types:
				if names := [x.voucher_no for x in self.vouchers if x.voucher_type == vtype]:
					latest_voucher = frappe.db.get_all(
						vtype,
						filters={"name": ["in", names]},
						pluck="posting_date",
						order_by="posting_date desc",
						limit=1,
					)[0]
					if latest_voucher and latest_pcv[0] >= latest_voucher:
						frappe.throw(_("Cannot Resubmit Ledger entries for vouchers in Closed fiscal year."))

	def validate_vouchers(self):
		if not self.vouchers:
			frappe.throw(_("Add atleast one voucher to repost."))

		validate_docs_for_voucher_types([x.voucher_type for x in self.vouchers])

		self.validate_no_duplicate_vouchers()
		self.validate_vouchers_are_submitted()

	def validate_no_duplicate_vouchers(self):
		vouchers = [(x.voucher_type, x.voucher_no) for x in self.vouchers]

		if len(vouchers) != len(set(vouchers)):
			frappe.throw(_("Duplicate vouchers found. Remove the duplicate vouchers to continue to repost."))

	def validate_vouchers_are_submitted(self):
		voucher_type_wise_map = {}
		for d in self.vouchers:
			voucher_type_wise_map.setdefault(d.voucher_type, [])
			voucher_type_wise_map[d.voucher_type].append(d.voucher_no)

		non_submitted_vouchers = []
		for key in voucher_type_wise_map.keys():
			non_submitted_vouchers.extend(
				frappe.get_all(
					key,
					filters={"name": ["in", voucher_type_wise_map[key]], "docstatus": ["!=", 1]},
					pluck="name",
				)
			)

		if non_submitted_vouchers:
			frappe.throw(
				_("The following vouchers are not submitted: {0}").format(
					comma_and(non_submitted_vouchers, add_quotes=True)
				)
			)

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def get_existing_ledger_entries(self):
		vouchers = [x.voucher_no for x in self.vouchers]
		gl = qb.DocType("GL Entry")
		existing_gles = (
			qb.from_(gl)
			.select(gl.star)
			.where((gl.voucher_no.isin(vouchers)) & (gl.is_cancelled == 0))
			.run(as_dict=True)
		)
		self.gles = frappe._dict({})

		for gle in existing_gles:
			self.gles.setdefault((gle.voucher_type, gle.voucher_no), frappe._dict({})).setdefault(
				"existing", []
			).append(gle.update({"old": True}))

	def generate_preview_data(self):
		frappe.flags.through_repost_accounting_ledger = True
		self.gl_entries = []
		self.get_existing_ledger_entries()
		for x in self.vouchers:
			doc = frappe.get_doc(x.voucher_type, x.voucher_no)
			if doc.doctype in ["Payment Entry", "Journal Entry"]:
				gle_map = doc.build_gl_map()
			elif doc.doctype == "Purchase Receipt":
				inventory_account_map = doc.get_inventory_account_map()
				gle_map = doc.get_gl_entries(inventory_account_map)
			else:
				gle_map = doc.get_gl_entries()

			old_entries = self.gles.get((x.voucher_type, x.voucher_no))
			if old_entries:
				self.gl_entries.extend(old_entries.existing)
			self.gl_entries.extend(gle_map)

	@frappe.whitelist()
	def generate_preview(self):
		from erpnext.accounts.report.general_ledger.general_ledger import get_columns as get_gl_columns

		if not self.vouchers:
			frappe.msgprint(_("Add vouchers to generate preview."))
			return

		gl_columns = []
		gl_data = []

		self.generate_preview_data()
		if self.gl_entries:
			filters = {"company": self.company, "include_dimensions": 1}
			for x in get_gl_columns(filters):
				if x["fieldname"] == "gl_entry":
					x["fieldname"] = "name"
				gl_columns.append(x)

			gl_data = self.gl_entries
		rendered_page = frappe.render_template(
			"erpnext/accounts/doctype/repost_accounting_ledger/repost_accounting_ledger.html",
			{"gl_columns": gl_columns, "gl_data": gl_data},
		)

		return rendered_page

	def on_submit(self):
		self.start_repost()

	def before_cancel(self):
		self._raise_error_if_reposting_in_progress()

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def _raise_error_if_reposting_in_progress(self):
		if self.scheduled_job and is_job_enqueued(self.scheduled_job):
			frappe.throw(_("Reposting is still in progress in background."))

	@frappe.whitelist()
	def start_repost(self):
		if self.docstatus != 1:
			frappe.throw(_("Reposting can be started only for submitted document."))

		if self.status in ["Queued", "In Progress", "Completed", "Cancelled"]:
			frappe.throw(_("Reposting cannot be started when status is {0}.").format(self.status))

		self._raise_error_if_reposting_in_progress()

		self.check_permission("write")
		self.db_set("status", "Queued")

		if frappe.in_test:
			repost(repost_doc_name=self.name)
			return

		job_id = frappe.generate_hash()
		frappe.enqueue(
			method="erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger.repost",
			repost_doc_name=self.name,
			is_async=True,
			job_name=f"repost_accounting_ledger_{self.name}",
			job_id=job_id,
			enqueue_after_commit=True,
		)
		self.db_set("scheduled_job", job_id)
		frappe.msgprint(_("Repost has started in the background"), alert=True, indicator="blue")


def _lock_vouchers(vouchers):
	"""Lock every voucher up front so a concurrent repost cannot touch the same GL entries."""
	locked_docs = []
	try:
		for x in vouchers:
			doc = frappe.get_doc(x.voucher_type, x.voucher_no)
			doc.lock()
			locked_docs.append(doc)
	except frappe.DocumentLockedError:
		for doc in locked_docs:
			doc.unlock()
		raise
	return locked_docs


def repost(repost_doc_name: str):
	locked_docs = []
	try:
		from erpnext.accounts.utils import _delete_accounting_ledger_entries, _delete_adv_pl_entries

		frappe.flags.through_repost_accounting_ledger = True

		repost_doc = frappe.get_doc("Repost Accounting Ledger", repost_doc_name)

		locked_docs = _lock_vouchers(repost_doc.vouchers)

		repost_doc.db_set("status", "In Progress", commit=True)

		for x in repost_doc.vouchers:
			if x.reposted:
				continue

			save_point = "reposting"
			frappe.db.savepoint(save_point=save_point)
			try:
				doc = frappe.get_doc(x.voucher_type, x.voucher_no)

				if doc.docstatus == 2:
					x.db_set(
						{
							"reposted": 1,
							"traceback": _("{0} {1} has been cancelled, nothing to repost.").format(
								x.voucher_type, x.voucher_no
							),
						},
						commit=True,
					)
					continue

				if repost_doc.delete_cancelled_entries:
					_delete_accounting_ledger_entries(doc.doctype, doc.name)
					_delete_adv_pl_entries(doc.doctype, doc.name)

				_repost_vouchers(doc, repost_doc.delete_cancelled_entries)
			except Exception:
				frappe.db.rollback(save_point=save_point)

				traceback = frappe.get_traceback(with_context=True)

				x.db_set("traceback", traceback)
			else:
				x.db_set({"reposted": 1, "traceback": ""})
			finally:
				if not frappe.in_test:
					frappe.db.commit()  # nosemgrep

	except Exception:
		if frappe.in_test:
			# Don't silently fail in tests,
			# there is no reason for reposts to fail in CI
			raise

		frappe.db.rollback()
		traceback = frappe.get_traceback(with_context=True)

		frappe.log_error(
			title=_("Unable to Repost Accounting Ledger"),
		)

		frappe.db.set_value(
			"Repost Accounting Ledger", repost_doc_name, {"error_log": traceback, "status": "Failed"}
		)
	else:
		reposted = sum(1 for voucher in repost_doc.vouchers if voucher.reposted)

		if reposted == len(repost_doc.vouchers):
			status = "Completed"
		elif reposted == 0:
			status = "Failed"
		else:
			status = "Partially Reposted"

		repost_doc.db_set({"status": status, "error_log": ""}, notify=True)
	finally:
		for doc in locked_docs:
			doc.unlock()
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep


def _repost_vouchers(doc, delete_cancelled_entries: bool | int | None):
	if doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
		_repost_invoices(doc, delete_cancelled_entries)

	elif doc.doctype == "Purchase Receipt":
		_repost_purchase_receipt(doc, delete_cancelled_entries)

	elif doc.doctype in ["Payment Entry", "Journal Entry"]:
		_repost_pe_je(doc, delete_cancelled_entries)

	elif doc.doctype in frappe.get_hooks("repost_allowed_doctypes"):
		_repost_allowed_hook_doctypes(doc, delete_cancelled_entries)


def _repost_invoices(invoice_doc, delete_cancelled_entries):
	if not delete_cancelled_entries:
		invoice_doc.docstatus = 2
		invoice_doc.make_gl_entries_on_cancel(from_repost=True)

	invoice_doc.docstatus = 1
	if invoice_doc.doctype == "Sales Invoice":
		invoice_doc.force_set_against_income_account()
	else:
		invoice_doc.force_set_against_expense_account()
	invoice_doc.make_gl_entries()


def _repost_purchase_receipt(receipt_doc, delete_cancelled_entries):
	if not delete_cancelled_entries:
		receipt_doc.docstatus = 2
		receipt_doc.make_gl_entries_on_cancel(from_repost=True)

	receipt_doc.docstatus = 1
	receipt_doc.make_gl_entries(from_repost=True)


def _repost_pe_je(entry_doc, delete_cancelled_entries):
	if not delete_cancelled_entries:
		entry_doc.make_gl_entries(cancel=1)
	entry_doc.make_gl_entries()


def _repost_allowed_hook_doctypes(repost_doc, delete_cancelled_entries: bool | int | None):
	from erpnext.accounts.general_ledger import make_reverse_gl_entries

	if hasattr(repost_doc, "make_gl_entries") and callable(repost_doc.make_gl_entries):
		if not delete_cancelled_entries:
			if "cancel" in inspect.getfullargspec(repost_doc.make_gl_entries).args:
				repost_doc.make_gl_entries(cancel=1)
			else:
				make_reverse_gl_entries(voucher_type=repost_doc.doctype, voucher_no=repost_doc.name)
		repost_doc.make_gl_entries()


def get_allowed_types_from_settings(child_doc: bool = False):
	repost_docs = [
		x.document_type
		for x in frappe.db.get_all(
			"Repost Allowed Types",
			fields=["document_type"],
			distinct=True,
		)
	]
	result = repost_docs

	if repost_docs and child_doc:
		result.extend(get_child_docs(repost_docs))

	return result


def get_child_docs(doc: list) -> list:
	child_doc = []
	doc = get_child_tables_of_doctypes(doc)
	for child_list in doc.values():
		for child in child_list:
			if child.get("child_table"):
				child_doc.append(child["child_table"])
	return child_doc


def validate_docs_for_deferred_accounting(sales_docs, purchase_docs):
	docs_with_deferred_revenue = frappe.db.get_all(
		"Sales Invoice Item",
		filters={"parent": ["in", sales_docs], "docstatus": 1, "enable_deferred_revenue": True},
		fields=["parent"],
		as_list=1,
	)

	docs_with_deferred_expense = frappe.db.get_all(
		"Purchase Invoice Item",
		filters={"parent": ["in", purchase_docs], "docstatus": 1, "enable_deferred_expense": 1},
		fields=["parent"],
		as_list=1,
	)

	if docs_with_deferred_revenue or docs_with_deferred_expense:
		frappe.throw(
			_("Documents: {0} have deferred revenue/expense enabled for them. Cannot repost.").format(
				frappe.bold(
					comma_and([x[0] for x in docs_with_deferred_expense + docs_with_deferred_revenue])
				)
			)
		)


def validate_docs_for_voucher_types(doc_voucher_types):
	allowed_types = get_allowed_types_from_settings()
	# Validate voucher types
	voucher_types = set(doc_voucher_types)
	if disallowed_types := voucher_types.difference(allowed_types):
		message = "are" if len(disallowed_types) > 1 else "is"
		frappe.throw(
			_(
				"{0} {1} not allowed to be reposted. You can enable it by adding it '{2}' table in {3}."
			).format(
				frappe.bold(comma_and(list(disallowed_types))),
				message,
				frappe.bold("Allowed Doctype"),
				frappe.utils.get_link_to_form("Accounts Settings"),
			)
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_repost_allowed_types(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
):
	if txt:
		filters.update({"document_type": ("like", f"%{txt}%")})

	if allowed_types := frappe.db.get_all(
		"Repost Allowed Types",
		filters=filters,
		fields=["document_type"],
		as_list=1,
		distinct=True,
	):
		return allowed_types
	return []
