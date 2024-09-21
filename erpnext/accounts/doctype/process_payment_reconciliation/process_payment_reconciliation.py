# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe.utils.scheduler import is_scheduler_inactive


class ProcessPaymentReconciliation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		bank_cash_account: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		default_advance_account: DF.Link
		error_log: DF.LongText | None
		from_invoice_date: DF.Date | None
		from_payment_date: DF.Date | None
		party: DF.DynamicLink
		party_type: DF.Link
		receivable_payable_account: DF.Link
		status: DF.Literal[
			"", "Queued", "Running", "Paused", "Completed", "Partially Reconciled", "Failed", "Cancelled"
		]
		to_invoice_date: DF.Date | None
		to_payment_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_receivable_payable_account()
		self.validate_bank_cash_account()

	def validate_receivable_payable_account(self):
		if self.receivable_payable_account:
			if self.company != frappe.db.get_value("Account", self.receivable_payable_account, "company"):
				frappe.throw(
					_("Receivable/Payable Account: {0} doesn't belong to company {1}").format(
						frappe.bold(self.receivable_payable_account), frappe.bold(self.company)
					)
				)

	def validate_bank_cash_account(self):
		if self.bank_cash_account:
			if self.company != frappe.db.get_value("Account", self.bank_cash_account, "company"):
				frappe.throw(
					_("Bank/Cash Account {0} doesn't belong to company {1}").format(
						frappe.bold(self.bank_cash_account), frappe.bold(self.company)
					)
				)

	def before_save(self):
		self.status = ""
		self.error_log = ""

	def on_submit(self):
		self.db_set("status", "Queued")
		self.db_set("error_log", None)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": self.name})
		if log:
			frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Cancelled")


@frappe.whitelist()
def get_reconciled_count(docname: str | None = None) -> float:
	current_status = {}
	if docname:
		reconcile_log = frappe.db.get_value(
			"Process Payment Reconciliation Log", filters={"process_pr": docname}, fieldname="name"
		)
		if reconcile_log:
			res = frappe.get_all(
				"Process Payment Reconciliation Log",
				filters={"name": reconcile_log},
				fields=["reconciled_entries", "total_allocations"],
				as_list=1,
			)
			current_status["processed"], current_status["total"] = res[0]

	return current_status


def get_pr_instance(doc: str):
	process_payment_reconciliation = frappe.get_doc("Process Payment Reconciliation", doc)

	pr = frappe.get_doc("Payment Reconciliation")
	fields = [
		"company",
		"party_type",
		"party",
		"receivable_payable_account",
		"default_advance_account",
		"from_invoice_date",
		"to_invoice_date",
		"from_payment_date",
		"to_payment_date",
	]
	d = {}
	for field in fields:
		d[field] = process_payment_reconciliation.get(field)
	pr.update(d)
	pr.invoice_limit = 1000
	pr.payment_limit = 1000
	return pr


def is_job_running(job_name: str) -> bool:
	jobs = frappe.db.get_all("RQ Job", filters={"status": ["in", ["started", "queued"]]})
	for x in jobs:
		if x.job_name == job_name:
			return True
	return False


@frappe.whitelist()
def pause_job_for_doc(docname: str | None = None):
	if docname:
		frappe.db.set_value("Process Payment Reconciliation", docname, "status", "Paused")
		log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": docname})
		if log:
			frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Paused")


@frappe.whitelist()
def trigger_job_for_doc(docname: str | None = None):
	"""
	Trigger background job
	"""
	if not docname:
		return

	if not frappe.db.get_single_value("Accounts Settings", "auto_reconcile_payments"):
		frappe.throw(
			_("Auto Reconciliation of Payments has been disabled. Enable it through {0}").format(
				get_link_to_form("Accounts Settings", "Accounts Settings")
			)
		)

		return

	if not is_scheduler_inactive():
		if frappe.db.get_value("Process Payment Reconciliation", docname, "status") == "Queued":
			frappe.db.set_value("Process Payment Reconciliation", docname, "status", "Running")
			job_name = f"start_processing_{docname}"
			if not is_job_running(job_name):
				frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile_based_on_filters",
					queue="long",
					is_async=True,
					job_name=job_name,
					enqueue_after_commit=True,
					doc=docname,
				)

		elif frappe.db.get_value("Process Payment Reconciliation", docname, "status") == "Paused":
			frappe.db.set_value("Process Payment Reconciliation", docname, "status", "Running")
			log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": docname})
			if log:
				frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Running")

			# Resume tasks for running doc
			job_name = f"start_processing_{docname}"
			if not is_job_running(job_name):
				frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile_based_on_filters",
					queue="long",
					is_async=True,
					job_name=job_name,
					doc=docname,
				)
	else:
		frappe.msgprint(_("Scheduler is Inactive. Can't trigger job now."))


def trigger_reconciliation_for_queued_docs():
	"""
	Will be called from Cron Job
	Fetch queued docs and start reconciliation process for each one
	"""
	if not frappe.db.get_single_value("Accounts Settings", "auto_reconcile_payments"):
		frappe.msgprint(
			_("Auto Reconciliation of Payments has been disabled. Enable it through {0}").format(
				get_link_to_form("Accounts Settings", "Accounts Settings")
			)
		)

		return

	if not is_scheduler_inactive():
		# Get all queued documents
		all_queued = frappe.db.get_all(
			"Process Payment Reconciliation",
			filters={"docstatus": 1, "status": "Queued"},
			order_by="creation desc",
			as_list=1,
		)

		docs_to_trigger = []
		unique_filters = set()
		queue_size = 5

		fields = ["company", "party_type", "party", "receivable_payable_account"]

		def get_filters_as_tuple(fields, doc):
			filters = ()
			for x in fields:
				filters += tuple(doc.get(x))
			return filters

		for x in all_queued:
			doc = frappe.get_doc("Process Payment Reconciliation", x)
			filters = get_filters_as_tuple(fields, doc)
			if filters not in unique_filters:
				unique_filters.add(filters)
				docs_to_trigger.append(doc.name)
			if len(docs_to_trigger) == queue_size:
				break

		# trigger reconcilation process for queue_size unique filters
		for doc in docs_to_trigger:
			trigger_job_for_doc(doc)

	else:
		frappe.msgprint(_("Scheduler is Inactive. Can't trigger jobs now."))


def reconcile_based_on_filters(doc: None | str = None) -> None:
	"""
	Identify current state of document and execute next tasks in background
	"""
	if doc:
		log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": doc})
		if not log:
			log = frappe.new_doc("Process Payment Reconciliation Log")
			log.process_pr = doc
			log.status = "Running"
			log = log.save()

			job_name = f"process_{doc}_fetch_and_allocate"
			if not is_job_running(job_name):
				frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.fetch_and_allocate",
					queue="long",
					timeout="3600",
					is_async=True,
					job_name=job_name,
					enqueue_after_commit=True,
					doc=doc,
				)
		else:
			res = frappe.get_all(
				"Process Payment Reconciliation Log",
				filters={"name": log},
				fields=["allocated", "reconciled"],
				as_list=1,
			)
			allocated, reconciled = res[0]

			if not allocated:
				job_name = f"process__{doc}_fetch_and_allocate"
				if not is_job_running(job_name):
					frappe.enqueue(
						method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.fetch_and_allocate",
						queue="long",
						timeout="3600",
						is_async=True,
						job_name=job_name,
						enqueue_after_commit=True,
						doc=doc,
					)
			elif not reconciled:
				allocation = get_next_allocation(log)
				if allocation:
					reconcile_job_name = (
						f"process_{doc}_reconcile_allocation_{allocation[0].idx}_{allocation[-1].idx}"
					)
				else:
					reconcile_job_name = f"process_{doc}_reconcile"
				if not is_job_running(reconcile_job_name):
					frappe.enqueue(
						method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile",
						queue="long",
						timeout="3600",
						is_async=True,
						job_name=reconcile_job_name,
						enqueue_after_commit=True,
						doc=doc,
					)
			elif reconciled:
				frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")


def get_next_allocation(log: str) -> list:
	if log:
		allocations = []
		next = frappe.db.get_all(
			"Process Payment Reconciliation Log Allocations",
			filters={"parent": log, "reconciled": 0},
			fields=["reference_type", "reference_name"],
			order_by="idx",
			limit=1,
		)

		if next:
			allocations = frappe.db.get_all(
				"Process Payment Reconciliation Log Allocations",
				filters={
					"parent": log,
					"reconciled": 0,
					"reference_type": next[0].reference_type,
					"reference_name": next[0].reference_name,
				},
				fields=["*"],
				order_by="idx",
			)

		return allocations
	return []


def fetch_and_allocate(doc: str) -> None:
	"""
	Fetch Invoices and Payments based on filters applied. FIFO ordering is used for allocation.
	"""

	if doc:
		log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": doc})
		if log:
			if not frappe.db.get_value("Process Payment Reconciliation Log", log, "allocated"):
				reconcile_log = frappe.get_doc("Process Payment Reconciliation Log", log)

				pr = get_pr_instance(doc)
				pr.get_unreconciled_entries()

				if len(pr.invoices) > 0 and len(pr.payments) > 0:
					invoices = [x.as_dict() for x in pr.invoices]
					payments = [x.as_dict() for x in pr.payments]
					pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

					for x in pr.get("allocation"):
						reconcile_log.append(
							"allocations",
							x.as_dict().update(
								{
									"parenttype": "Process Payment Reconciliation Log",
									"parent": reconcile_log.name,
									"name": None,
									"reconciled": False,
								}
							),
						)
				reconcile_log.allocated = True
				reconcile_log.total_allocations = len(reconcile_log.get("allocations"))
				reconcile_log.reconciled_entries = 0
				reconcile_log.save()

				# generate reconcile job name
				allocation = get_next_allocation(log)
				if allocation:
					reconcile_job_name = (
						f"process_{doc}_reconcile_allocation_{allocation[0].idx}_{allocation[-1].idx}"
					)
				else:
					reconcile_job_name = f"process_{doc}_reconcile"

				if not is_job_running(reconcile_job_name):
					frappe.enqueue(
						method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile",
						queue="long",
						timeout="3600",
						is_async=True,
						job_name=reconcile_job_name,
						enqueue_after_commit=True,
						doc=doc,
					)


def reconcile(doc: None | str = None) -> None:
	if doc:
		log = frappe.db.get_value("Process Payment Reconciliation Log", filters={"process_pr": doc})
		if log:
			res = frappe.get_all(
				"Process Payment Reconciliation Log",
				filters={"name": log},
				fields=["reconciled_entries", "total_allocations"],
				as_list=1,
				limit=1,
			)

			reconciled_entries, total_allocations = res[0]
			if reconciled_entries != total_allocations:
				try:
					# Fetch next allocation
					allocations = get_next_allocation(log)

					pr = get_pr_instance(doc)

					# pass allocation to PR instance
					for x in allocations:
						pr.append("allocation", x)

					# reconcile
					pr.reconcile_allocations(skip_ref_details_update_for_pe=True)

					# If Payment Entry, update details only for newly linked references
					# This is for performance
					if allocations[0].reference_type == "Payment Entry":
						references = [(x.invoice_type, x.invoice_number) for x in allocations]
						pe = frappe.get_doc(allocations[0].reference_type, allocations[0].reference_name)
						pe.flags.ignore_validate_update_after_submit = True
						pe.set_missing_ref_details(update_ref_details_only_for=references)
						pe.save()

					# Update reconciled flag
					allocation_names = [x.name for x in allocations]
					ppa = qb.DocType("Process Payment Reconciliation Log Allocations")
					qb.update(ppa).set(ppa.reconciled, True).where(ppa.name.isin(allocation_names)).run()

					# Update reconciled count
					reconciled_count = frappe.db.count(
						"Process Payment Reconciliation Log Allocations",
						filters={"parent": log, "reconciled": True},
					)
					frappe.db.set_value(
						"Process Payment Reconciliation Log", log, "reconciled_entries", reconciled_count
					)

				except Exception:
					# Update the parent doc about the exception
					frappe.db.rollback()

					traceback = frappe.get_traceback(with_context=True)
					if traceback:
						message = "Traceback: <br>" + traceback
						frappe.db.set_value("Process Payment Reconciliation Log", log, "error_log", message)
						frappe.db.set_value(
							"Process Payment Reconciliation",
							doc,
							"error_log",
							message,
						)
					if reconciled_entries and total_allocations and reconciled_entries < total_allocations:
						frappe.db.set_value(
							"Process Payment Reconciliation Log", log, "status", "Partially Reconciled"
						)
						frappe.db.set_value(
							"Process Payment Reconciliation",
							doc,
							"status",
							"Partially Reconciled",
						)
					else:
						frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Failed")
						frappe.db.set_value(
							"Process Payment Reconciliation",
							doc,
							"status",
							"Failed",
						)
				finally:
					if reconciled_entries == total_allocations:
						frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Reconciled")
						frappe.db.set_value("Process Payment Reconciliation Log", log, "reconciled", True)
						frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")
					else:
						if not (
							frappe.db.get_value("Process Payment Reconciliation", doc, "status") == "Paused"
						):
							# trigger next batch in job
							# generate reconcile job name
							allocation = get_next_allocation(log)
							if allocation:
								reconcile_job_name = f"process_{doc}_reconcile_allocation_{allocation[0].idx}_{allocation[-1].idx}"
							else:
								reconcile_job_name = f"process_{doc}_reconcile"

							if not is_job_running(reconcile_job_name):
								frappe.enqueue(
									method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile",
									queue="long",
									timeout="3600",
									is_async=True,
									job_name=reconcile_job_name,
									enqueue_after_commit=True,
									doc=doc,
								)
			else:
				frappe.db.set_value("Process Payment Reconciliation Log", log, "status", "Reconciled")
				frappe.db.set_value("Process Payment Reconciliation Log", log, "reconciled", True)
				frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")


@frappe.whitelist()
def is_any_doc_running(for_filter: str | dict | None = None) -> str | None:
	running_doc = None
	if for_filter:
		if isinstance(for_filter, str):
			for_filter = json.loads(for_filter)

		running_doc = frappe.db.get_value(
			"Process Payment Reconciliation",
			filters={
				"docstatus": 1,
				"status": ["in", ["Running", "Paused"]],
				"company": for_filter.get("company"),
				"party_type": for_filter.get("party_type"),
				"party": for_filter.get("party"),
				"receivable_payable_account": for_filter.get("receivable_payable_account"),
			},
			fieldname="name",
		)
	else:
		running_doc = frappe.db.get_value(
			"Process Payment Reconciliation", filters={"docstatus": 1, "status": "Running"}
		)
	return running_doc
