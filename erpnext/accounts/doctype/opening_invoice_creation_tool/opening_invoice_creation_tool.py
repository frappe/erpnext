# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils import cint, escape_html, flt, nowdate
from frappe.utils.background_jobs import enqueue, is_job_enqueued

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.stock.utils import get_default_stock_uom


class OpeningInvoiceCreationTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.opening_invoice_creation_tool_item.opening_invoice_creation_tool_item import (
			OpeningInvoiceCreationToolItem,
		)

		company: DF.Link
		cost_center: DF.Link | None
		create_missing_party: DF.Check
		invoice_type: DF.Literal["Sales", "Purchase"]
		invoices: DF.Table[OpeningInvoiceCreationToolItem]
		project: DF.Link | None
		status: DF.Literal["Pending", "In Progress", "Success", "Partial Success", "Error"]
	# end: auto-generated types

	def validate(self):
		if self.get_doc_before_save() and self.get_doc_before_save().status != "Pending":
			frappe.throw(_("Started import runs cannot be changed."))

	def on_trash(self):
		frappe.db.delete("Opening Invoice Creation Log", {"opening_invoice_creation_tool": self.name})

	def onload(self):
		"""Load the Opening Invoice summary"""
		if self.is_new() or self.status == "Pending":
			summary, max_count = self.get_opening_invoice_summary()
			self.set_onload("opening_invoices_summary", summary)
			self.set_onload("max_count", max_count)
		self.set_onload("import_result_summary", self.get_import_result_summary())
		self.set_onload("temporary_opening_account", get_temporary_opening_account(self.company))

	def get_import_result_summary(self):
		if self.is_new() or self.status not in ("Success", "Partial Success", "Error"):
			return None

		result = frappe.get_all(
			"Opening Invoice Creation Log",
			filters={"opening_invoice_creation_tool": self.name},
			fields=[{"COUNT": "*", "as": "total"}, {"SUM": "success", "as": "successes"}],
		)[0]
		successes = cint(result.successes)
		return {
			"total": cint(result.total),
			"successes": successes,
			"failures": cint(result.total) - successes,
		}

	def get_opening_invoice_summary(self):
		def prepare_invoice_summary(doctype, invoices):
			# add company wise sales / purchase invoice summary
			paid_amount = []
			outstanding_amount = []
			for invoice in invoices:
				company = invoice.pop("company")
				_summary = invoices_summary.get(company, {})
				_summary.update({"currency": company_wise_currency.get(company), doctype: invoice})
				invoices_summary.update({company: _summary})

				if invoice.paid_amount:
					paid_amount.append(invoice.paid_amount)
				if invoice.outstanding_amount:
					outstanding_amount.append(invoice.outstanding_amount)

			if paid_amount or outstanding_amount:
				max_count.update(
					{
						doctype: {
							"max_paid": max(paid_amount) if paid_amount else 0.0,
							"max_due": max(outstanding_amount) if outstanding_amount else 0.0,
						}
					}
				)

		invoices_summary = {}
		max_count = {}
		fields = [
			"company",
			{"COUNT": "*", "as": "total_invoices"},
			{"SUM": "outstanding_amount", "as": "outstanding_amount"},
		]
		companies = frappe.get_all("Company", fields=["name as company", "default_currency as currency"])
		if not companies:
			return None, None

		company_wise_currency = {row.company: row.currency for row in companies}
		for doctype in ["Sales Invoice", "Purchase Invoice"]:
			invoices = frappe.get_all(
				doctype, filters=dict(is_opening="Yes", docstatus=1), fields=fields, group_by="company"
			)
			prepare_invoice_summary(doctype, invoices)

		invoices_summary_companies = list(invoices_summary.keys())

		for company in invoices_summary_companies:
			invoices_summary[escape_html(company)] = invoices_summary.pop(company)

		return invoices_summary, max_count

	def validate_company(self):
		if not self.company:
			frappe.throw(_("Please select the Company"))

	def set_missing_values(self, row):
		row.qty = row.qty or 1.0
		row.temporary_opening_account = row.temporary_opening_account or get_temporary_opening_account(
			self.company
		)
		row.party_type = "Customer" if self.invoice_type == "Sales" else "Supplier"
		row.item_name = row.item_name or _("Opening Invoice Item")
		row.posting_date = row.posting_date or nowdate()
		row.due_date = row.due_date or nowdate()

	def validate_mandatory_invoice_fields(self, row):
		if self.create_missing_party:
			if not row.party and not row.party_name:
				frappe.throw(_("Row #{0}: Either Party ID or Party Name is required").format(row.idx))

			if not row.party and row.party_name:
				row.party = self.add_party(row.party_type, row.party_name)

			if row.party and not frappe.db.exists(row.party_type, row.party):
				row.party = self.add_party(row.party_type, row.party)

		else:
			if not row.party:
				frappe.throw(_("Row #{0}: Party ID is required").format(row.idx))
			if not frappe.db.exists(row.party_type, row.party):
				frappe.throw(
					_("Row #{0}: {1} {2} does not exist.").format(
						row.idx, frappe.bold(row.party_type), frappe.bold(row.party)
					)
				)

		mandatory_error_msg = _("Row #{0}: {1} is required to create the Opening {2} Invoices")
		for d in ("Outstanding Amount", "Temporary Opening Account"):
			if not row.get(scrub(d)):
				frappe.throw(mandatory_error_msg.format(row.idx, d, self.invoice_type))

		self.validate_temporary_opening_account(row)

	def validate_temporary_opening_account(self, row):
		account_type = frappe.get_cached_value("Account", row.temporary_opening_account, "account_type")
		if account_type != "Temporary":
			frappe.throw(
				_("Row #{0}: {1} account is not of type {2}").format(
					row.idx, row.temporary_opening_account, "Temporary"
				)
			)

	def get_invoice(self, row):
		self.set_missing_values(row)
		self.validate_mandatory_invoice_fields(row)
		invoice = self.get_invoice_dict(row)
		company_details = (
			frappe.get_cached_value(
				"Company", self.company, ["default_currency", "default_letter_head"], as_dict=1
			)
			or {}
		)

		default_currency = frappe.db.get_value(row.party_type, row.party, "default_currency")
		if company_details:
			invoice.update(
				{
					"currency": default_currency or company_details.get("default_currency"),
					"letter_head": company_details.get("default_letter_head"),
				}
			)
		return invoice

	def add_party(self, party_type, party):
		party_doc = frappe.new_doc(party_type)
		if party_type == "Customer":
			party_doc.customer_name = party
		else:
			supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group")
			if not supplier_group:
				frappe.throw(_("Please Set Supplier Group in Buying Settings."))

			party_doc.supplier_name = party
			party_doc.supplier_group = supplier_group

		party_doc.flags.ignore_mandatory = True
		party_doc.save(ignore_permissions=True)
		return party_doc.name

	def get_invoice_dict(self, row=None):
		def get_item_dict():
			cost_center = row.get("cost_center") or frappe.get_cached_value(
				"Company", self.company, "cost_center"
			)
			if not cost_center:
				frappe.throw(
					_("Please set the Default Cost Center in {0} company.").format(frappe.bold(self.company))
				)

			income_expense_account_field = (
				"income_account" if row.party_type == "Customer" else "expense_account"
			)
			default_uom = get_default_stock_uom()
			rate = flt(row.outstanding_amount) / flt(row.qty)

			item_dict = frappe._dict(
				{
					"uom": default_uom,
					"rate": rate or 0.0,
					"qty": row.qty,
					"conversion_factor": 1.0,
					"item_name": row.item_name or "Opening Invoice Item",
					"description": row.item_name or "Opening Invoice Item",
					income_expense_account_field: row.temporary_opening_account,
					"cost_center": cost_center,
					"project": row.get("project") or self.get("project"),
				}
			)

			for dimension in get_accounting_dimensions():
				item_dict.update({dimension: row.get(dimension)})

			return item_dict

		item = get_item_dict()

		invoice = frappe._dict(
			{
				"items": [item],
				"is_opening": "Yes",
				"set_posting_time": 1,
				"company": self.company,
				"cost_center": self.cost_center,
				"due_date": row.due_date,
				"posting_date": row.posting_date,
				frappe.scrub(row.party_type): row.party,
				"is_pos": 0,
				"doctype": "Sales Invoice" if self.invoice_type == "Sales" else "Purchase Invoice",
				"update_stock": 0,  # important: https://github.com/frappe/erpnext/pull/23559
				"invoice_number": row.invoice_number,
				"disable_rounded_total": 1,
			}
		)

		if self.invoice_type == "Purchase" and row.supplier_invoice_date:
			invoice.update({"bill_date": row.supplier_invoice_date})

		accounting_dimension = get_accounting_dimensions()
		for dimension in accounting_dimension:
			invoice.update({dimension: self.get(dimension) or item.get(dimension)})

		return invoice

	@frappe.whitelist()
	def make_invoices(self):
		self.check_permission("write")
		frappe.db.sql(
			"select name from `tabOpening Invoice Creation Tool` where name=%s for update", self.name
		)
		run = frappe.get_doc(self.doctype, self.name)
		if run.status != "Pending":
			frappe.throw(_("This import run has already started."))

		run.validate_company()
		total = len([row for row in run.invoices if row])
		run.db_set("status", "In Progress", update_modified=False)
		if total < 50:
			return start_import(run.name)
		else:
			from frappe.utils.scheduler import is_scheduler_inactive

			if is_scheduler_inactive() and not frappe.in_test:
				frappe.throw(_("Scheduler is inactive. Cannot import data."), title=_("Scheduler Inactive"))

			job_id = f"opening_invoice::{run.name}"

			if not is_job_enqueued(job_id):
				enqueue(
					start_import,
					queue="default",
					timeout=6000,
					event="opening_invoice_creation",
					job_id=job_id,
					run_name=run.name,
					enqueue_after_commit=True,
					now=frappe.conf.developer_mode or frappe.in_test,
				)


@frappe.whitelist()
def create_and_start_import(doc: str | dict):
	"""Create a run without resolving party links, then process it immediately."""
	run = frappe.get_doc(frappe.parse_json(doc))
	if run.doctype != "Opening Invoice Creation Tool":
		frappe.throw(_("Invalid import run."))

	# Create Missing Party must run before Dynamic Link validation rejects new parties.
	run.flags.ignore_links = True
	run.insert()
	return {"name": run.name, "invoices": run.make_invoices()}


def start_import(run_name):
	run = frappe.get_doc("Opening Invoice Creation Tool", run_name)
	errors = 0
	names = []
	rows = [row for row in run.invoices if row]
	total = len(rows)
	for idx, row in enumerate(rows):
		# Scope each invoice to a savepoint so a failure only undoes that invoice.
		# A plain rollback() would discard the whole transaction — including invoices
		# imported earlier in this batch and the error logs of earlier failures (the
		# latter only survive on mariadb because the Error Log table is MyISAM; on
		# postgres they would be lost). Rolling back to a savepoint keeps both.
		savepoint = f"opening_invoice_{frappe.generate_hash(length=8)}"
		frappe.db.savepoint(savepoint)
		is_last = idx == total - 1
		frappe.clear_messages()
		try:
			d = run.get_invoice(row)
			invoice_number = d.invoice_number
			doc = frappe.get_doc(d)
			doc.flags.ignore_mandatory = True
			# the outstanding amount is entered inclusive of tax, so taxes must not
			# be added on top of it
			doc.flags.dont_auto_add_taxes = True
			doc.insert(set_name=invoice_number)
			doc.submit()
			create_log(run.name, idx + 1, success=True, invoice=doc)
			if not frappe.in_test:
				frappe.db.commit()
			names.append(doc.name)
			publish(
				run,
				idx,
				total,
				d.doctype,
				errors=errors if is_last else None,
				successes=idx + 1 - errors if is_last else None,
			)
		except Exception:
			errors += 1
			messages = frappe.get_message_log()
			frappe.db.rollback(save_point=savepoint)
			create_log(run.name, idx + 1, messages=messages, exception=frappe.get_traceback())
			frappe.clear_messages()
			publish(
				run,
				idx,
				total,
				"Sales Invoice" if run.invoice_type == "Sales" else "Purchase Invoice",
				errors=errors if is_last else None,
				successes=idx + 1 - errors if is_last else None,
			)

	successes = total - errors
	if errors == total:
		status = "Error"
	elif errors:
		status = "Partial Success"
	else:
		status = "Success"
	run.db_set("status", status, update_modified=False)
	frappe.msgprint(
		_("Opening invoice creation completed: {0} succeeded, {1} failed.").format(successes, errors),
		indicator="green" if not errors else "orange" if successes else "red",
		title=_("Opening Invoice Creation Complete"),
	)
	return names


def create_log(run_name, source_row_index, success=False, invoice=None, messages=None, exception=None):
	frappe.get_doc(
		{
			"doctype": "Opening Invoice Creation Log",
			"opening_invoice_creation_tool": run_name,
			"source_row_index": source_row_index,
			"success": success,
			"reference_type": invoice.doctype if invoice else None,
			"reference_name": invoice.name if invoice else None,
			"messages": frappe.as_json(messages) if messages else None,
			"exception": exception,
		}
	).insert(ignore_permissions=True)


def publish(run, index, total, doctype, errors=None, successes=None):
	frappe.publish_realtime(
		"opening_invoice_creation_progress",
		dict(
			title=_("Opening Invoice Creation In Progress"),
			message=_("Creating {} out of {} {}").format(index + 1, total, doctype),
			count=index + 1,
			total=total,
			errors=errors,
			successes=successes,
			run_name=run.name,
		),
		user=run.owner,
	)


@frappe.whitelist()
def get_temporary_opening_account(company: str | None = None):
	if not company:
		return

	accounts = frappe.get_all("Account", filters={"company": company, "account_type": "Temporary"})
	if not accounts:
		frappe.throw(_("Please add a Temporary Opening account in Chart of Accounts"))

	return accounts[0].name
