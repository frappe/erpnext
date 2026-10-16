# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate
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
		default_advance_account: DF.Link | None
		error_log: DF.LongText | None
		from_date: DF.Date | None
		from_invoice_date: DF.Date | None
		from_payment_date: DF.Date | None
		party: DF.DynamicLink
		party_type: DF.Link
		receivable_payable_account: DF.Link | None
		status: DF.Literal[
			"", "Queued", "Running", "Paused", "Completed", "Partially Reconciled", "Failed", "Cancelled"
		]
		to_date: DF.Date | None
		to_invoice_date: DF.Date | None
		to_payment_date: DF.Date | None
	# end: auto-generated types

	def on_discard(self):
		self.db_set("status", "Cancelled")

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


class AllocationLog:
	"""Moves Payment Reconciliation allocation rows in and out of the Process PR log.

	The log keeps upstream's fields: `reference_*` is the party's payment, `invoice_*`
	the other side. Accounts, parties and rates are not stored;
	`validate_allocation` rebuilds them from the ledger before each batch is reconciled.
	"""

	CARRIED = (
		"allocated_amount",
		"unreconciled_amount",
		"amount",
		"is_advance",
		"difference_amount",
		"difference_account",
		"gain_loss_posting_date",
		"exchange_rate",
		"currency",
	)

	def __init__(self, pr):
		from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import payment_side

		self.paid = payment_side(pr.party_type)
		self.other = "to_receive" if self.paid == "to_pay" else "to_pay"

	def to_log(self, allocation, log_name):
		return {
			"parenttype": "Process Payment Reconciliation Log",
			"parent": log_name,
			"name": None,
			"reconciled": False,
			"reference_type": allocation.get(f"{self.paid}_voucher_type"),
			"reference_name": allocation.get(f"{self.paid}_voucher_no"),
			"reference_row": allocation.get(f"{self.paid}_voucher_row"),
			"invoice_type": allocation.get(f"{self.other}_voucher_type"),
			"invoice_number": allocation.get(f"{self.other}_voucher_no"),
			"invoice_row": allocation.get(f"{self.other}_voucher_row"),
			**{field: allocation.get(field) for field in self.CARRIED},
		}

	def to_allocation(self, log_row):
		return {
			f"{self.paid}_voucher_type": log_row.reference_type,
			f"{self.paid}_voucher_no": log_row.reference_name,
			f"{self.paid}_voucher_row": log_row.reference_row,
			f"{self.other}_voucher_type": log_row.invoice_type,
			f"{self.other}_voucher_no": log_row.invoice_number,
			f"{self.other}_voucher_row": log_row.get("invoice_row"),
			**{field: log_row.get(field) for field in self.CARRIED},
		}


def get_pr_instance(doc: str):
	process_payment_reconciliation = frappe.get_doc("Process Payment Reconciliation", doc)

	pr = frappe.get_doc("Payment Reconciliation")
	fields = [
		"company",
		"party_type",
		"party",
		"receivable_payable_account",
		"default_advance_account",
		"from_date",
		"to_date",
		"cost_center",
	]
	d = {}
	for field in fields:
		d[field] = process_payment_reconciliation.get(field)

	# records saved before the refactor kept separate invoice and payment dates: take
	# the range covering the ones that were set
	def covering(fields, pick):
		values = [getdate(v) for v in (process_payment_reconciliation.get(field) for field in fields) if v]
		return pick(values) if values else None

	if not d["from_date"]:
		d["from_date"] = covering(("from_invoice_date", "from_payment_date"), min)
	if not d["to_date"]:
		d["to_date"] = covering(("to_invoice_date", "to_payment_date"), max)

	pr.update(d)
	pr.fetch_limit = 1000
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
		frappe.has_permission("Process Payment Reconciliation", "write", doc=docname, throw=True)
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

	frappe.has_permission("Process Payment Reconciliation", "write", doc=docname, throw=True)

	if not frappe.get_single_value("Accounts Settings", "auto_reconcile_payments"):
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
	if not frappe.get_single_value("Accounts Settings", "auto_reconcile_payments"):
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
		queue_size = frappe.get_single_value("Accounts Settings", "reconciliation_queue_size") or 5

		# one job per party: a run can fetch across all the party's accounts
		fields = ["company", "party_type", "party"]

		def get_filters_as_tuple(fields, doc):
			return tuple(doc.get(x) or "" for x in fields)

		for x in all_queued:
			doc = frappe.get_doc("Process Payment Reconciliation", x)
			filters = get_filters_as_tuple(fields, doc)
			if filters not in unique_filters and not is_any_doc_running(
				{field: doc.get(field) for field in [*fields, "receivable_payable_account"]}
			):
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

				if len(pr.to_receive) > 0 and len(pr.to_pay) > 0:
					to_receive = [x.as_dict() for x in pr.to_receive]
					to_pay = [x.as_dict() for x in pr.to_pay]
					pr.allocate_entries(frappe._dict({"to_receive": to_receive, "to_pay": to_pay}))

					allocation_log = AllocationLog(pr)
					for x in pr.get("allocation"):
						reconcile_log.append("allocations", allocation_log.to_log(x, reconcile_log.name))
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

					allocation_log = AllocationLog(pr)
					for x in allocations:
						pr.append("allocation", allocation_log.to_allocation(x))

					skip_ref_details_update_for_pe = check_multi_currency(pr)
					# reconcile
					from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import (
						ReconcileRouter,
					)

					# allocations were made earlier; refuse ones the ledger no longer backs
					pr.validate_allocation()
					ReconcileRouter(pr).execute(skip_ref_details_update_for_pe=skip_ref_details_update_for_pe)

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
					qb.update(ppa).set(ppa.reconciled, 1).where(
						ppa.name.isin(allocation_names)
					).run()  # smallint, not bool

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
						frappe.db.set_value("Process Payment Reconciliation Log", log, "reconciled", 1)
						frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")
					else:
						if frappe.db.get_value("Process Payment Reconciliation", doc, "status") != "Paused":
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
				frappe.db.set_value("Process Payment Reconciliation Log", log, "reconciled", 1)
				frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")


def check_multi_currency(pr_doc):
	GL = frappe.qb.DocType("GL Entry")
	Account = frappe.qb.DocType("Account")

	def get_account_currency(voucher_type, voucher_no):
		currency = (
			frappe.qb.from_(GL)
			.join(Account)
			.on(GL.account == Account.name)
			.select(Account.account_currency)
			.where(
				(GL.voucher_type == voucher_type)
				& (GL.voucher_no == voucher_no)
				& (Account.account_type.isin(["Payable", "Receivable"]))
			)
			.limit(1)
		).run(as_dict=True)

		return currency[0].account_currency if currency else None

	for allocation in pr_doc.allocation:
		pay_currency = get_account_currency(allocation.to_pay_voucher_type, allocation.to_pay_voucher_no)
		recv_currency = get_account_currency(
			allocation.to_receive_voucher_type, allocation.to_receive_voucher_no
		)

		if pay_currency != recv_currency:
			return True

	return False


@frappe.whitelist()
def is_any_doc_running(for_filter: str | dict | None = None) -> str | None:
	"""Find a running/paused Process PR for the same party.

	Cross-account semantics: if `for_filter.receivable_payable_account` is None or empty
	("*" wildcard intent), match ANY running job for the party — that catches both
	per-account jobs (legacy) and cross-account jobs (new). If a specific account is
	supplied, match that exact account OR any cross-account job (which would conflict).
	This prevents two jobs from operating on overlapping vouchers.
	"""
	if not for_filter:
		return frappe.db.get_value(
			"Process Payment Reconciliation", filters={"docstatus": 1, "status": "Running"}
		)

	for_filter = frappe.parse_json(for_filter)

	filters = {
		"docstatus": 1,
		"status": ["in", ["Running", "Paused"]],
		"company": for_filter.get("company"),
		"party_type": for_filter.get("party_type"),
		"party": for_filter.get("party"),
	}

	requested_account = for_filter.get("receivable_payable_account")
	if requested_account:
		# Match either same account OR cross-account (blank) job — both would conflict.
		filters["receivable_payable_account"] = ["in", [requested_account, "", None]]
	# else: requested job is cross-account → matches any running job for the party
	# (no `receivable_payable_account` filter added).

	return frappe.db.get_value("Process Payment Reconciliation", filters=filters, fieldname="name")
