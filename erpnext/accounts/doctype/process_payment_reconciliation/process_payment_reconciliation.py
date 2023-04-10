# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe.utils.scheduler import is_scheduler_inactive


class ProcessPaymentReconciliation(Document):
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


@frappe.whitelist()
def get_progress(docname: str | None = None) -> float:
	progress = 0.0
	if docname:
		reconcile_log = frappe.db.get_value(
			"Process Payment Reconciliation Log", filters={"process_pr": docname}, fieldname="name"
		)
		if reconcile_log:
			processed = frappe.db.get_value(
				"Process Payment Reconciliation Log", reconcile_log, "reconciled_entries"
			)
			total = frappe.db.get_value(
				"Process Payment Reconciliation Log", reconcile_log, "total_allocations"
			)

			if processed != 0:
				progress = processed / total * 100
			elif total == 0:
				progress = 100

			return progress

	return progress


def get_pr_instance(doc: str):
	process_payment_reconciliation = frappe.get_doc("Process Payment Reconciliation", doc)

	pr = frappe.get_doc("Payment Reconciliation")
	fields = [
		"company",
		"party_type",
		"party",
		"receivable_payable_account",
		"from_invoice_date",
		"to_invoice_date",
		"from_payment_date",
		"to_payment_date",
	]
	d = {}
	for field in fields:
		d[field] = process_payment_reconciliation.get(field)
	pr.update(d)
	return pr


def is_job_running(job_name: str) -> bool:
	jobs = frappe.db.get_all("RQ Job", filters={"status": ["in", ["started", "queued"]]})
	for x in jobs:
		if x.job_name == job_name:
			return True
	return False


@frappe.whitelist()
def trigger_job_for_doc(docname: str | None = None):
	"""
	Trigger background job
	"""
	if not docname:
		return

	if not frappe.db.get_single_value(
		"Accounts Settings", "enable_payment_reconciliation_in_background"
	):
		frappe.throw(
			_(
				"Payment Reconciliation through backgound Job has been disabled. Enable it through {}"
			).format(get_link_to_form("Accounts Settings", "Accounts Settings"))
		)

		return

	if not is_scheduler_inactive():
		if frappe.db.get_value("Process Payment Reconciliation", docname, "status") == "Queued":
			frappe.db.set_value("Process Payment Reconciliation", docname, "status", "Running")
			job_name = f"start_processing_{docname}"
			if not is_job_running(job_name):
				job = frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile_based_on_filters",
					queue="long",
					is_async=True,
					job_name=job_name,
					enqueue_after_commit=True,
					doc=docname,
				)
				frappe.msgprint(_("Background Job {0} triggered").format(job_name))
		elif frappe.db.get_value("Process Payment Reconciliation", docname, "status") == "Running":
			# Resume tasks for running doc
			job_name = f"start_processing_{docname}"
			if not is_job_running(job_name):
				job = frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile_based_on_filters",
					queue="long",
					is_async=True,
					job_name=job_name,
					doc=docname,
				)
				frappe.msgprint(_("Background Job {0} triggered").format(job_name))
	else:
		frappe.msgprint(_("Scheduler is Inactive. Can't trigger job now."))


@frappe.whitelist()
def trigger_reconciliation_for_queued_docs():
	"""
	Will be called from Cron Job
	Fetch queued docs and start reconciliation process for each one
	"""
	if not frappe.db.get_single_value(
		"Accounts Settings", "enable_payment_reconciliation_in_background"
	):
		frappe.throw(
			_(
				"Payment Reconciliation through backgound Job has been disabled. Enable it through {0}"
			).format(get_link_to_form("Accounts Settings", "Accounts Settings"))
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
		log = frappe.db.get_all(
			"Process Payment Reconciliation Log", filters={"process_pr": doc}, as_list=1
		)
		if not log:
			log = frappe.new_doc("Process Payment Reconciliation Log")
			log.process_pr = doc
			log.status = "Running"
			log = log.save()

			job_name = f"process_{doc}_fetch_and_allocate"
			if not is_job_running(job_name):
				job = frappe.enqueue(
					method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.fetch_and_allocate",
					queue="long",
					timeout="3600",
					is_async=True,
					job_name=job_name,
					enqueue_after_commit=True,
					doc=doc,
				)
		else:
			reconcile_log = frappe.get_doc("Process Payment Reconciliation Log", log[0][0])
			if not reconcile_log.allocated:

				job_name = f"process__{doc}_fetch_and_allocate"
				if not is_job_running(job_name):
					job = frappe.enqueue(
						method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.fetch_and_allocate",
						queue="long",
						timeout="3600",
						is_async=True,
						job_name=job_name,
						enqueue_after_commit=True,
						doc=doc,
					)
			elif not reconcile_log.reconciled:
				batch = split_allocations_into_batches(
					[x for x in reconcile_log.get("allocations") if not x.reconciled]
				)
				if batch:
					start = batch[0].idx
					end = batch[-1].idx
					reconcile_job_name = f"process_{doc}_reconcile_{start}_{end}"
				else:
					reconcile_job_name = f"process_{doc}_reconcile"
				if not is_job_running(reconcile_job_name):
					job = frappe.enqueue(
						method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile",
						queue="long",
						timeout="3600",
						is_async=True,
						job_name=reconcile_job_name,
						enqueue_after_commit=True,
						doc=doc,
					)
			elif reconcile_log.reconciled:
				frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")


def split_allocations_into_batches(unreconciled_allocations: list) -> list:
	"""
	Split a list of payment allocations into groups(batch) by reference_name and return the first group
	"""
	if unreconciled_allocations:
		batch = []
		previous_entry = None
		for x in unreconciled_allocations:
			if not previous_entry or ((x.reference_type, x.reference_name) == previous_entry):
				batch.append(x)
				previous_entry = (x.reference_type, x.reference_name)
			else:
				break

		return batch
	return []


def fetch_and_allocate(doc: str) -> None:
	"""
	Fetch Invoices and Payments based on filters applied. FIFO ordering is used for allocation.
	"""

	if doc:
		log = frappe.db.get_all(
			"Process Payment Reconciliation Log", filters={"process_pr": doc}, as_list=1
		)
		if log:
			if not frappe.db.get_value("Process Payment Reconciliation Log", log[0][0], "allocated"):
				reconcile_log = frappe.get_doc("Process Payment Reconciliation Log", log[0][0])

				pr = get_pr_instance(doc)
				pr.get_unreconciled_entries()

				if len(pr.invoices) > 0 and len(pr.payments) > 0:
					invoices = [x.as_dict() for x in pr.invoices]
					payments = [x.as_dict() for x in pr.payments]
					pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

					for x in pr.get("invoices"):
						reconcile_log.append(
							"invoices",
							x.as_dict().update(
								{
									"parenttype": "Process Payment Reconciliation Log",
									"parent": reconcile_log.name,
									"name": None,
								}
							),
						)

					for x in pr.get("payments"):
						reconcile_log.append(
							"payments",
							x.as_dict().update(
								{
									"parenttype": "Process Payment Reconciliation Log",
									"parent": reconcile_log.name,
									"name": None,
								}
							),
						)

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
				batch = split_allocations_into_batches(
					[x for x in reconcile_log.get("allocations") if not x.reconciled]
				)
				if batch:
					start = batch[0].idx
					end = batch[-1].idx
					reconcile_job_name = f"process_{doc}_reconcile_{start}_{end}"
				else:
					reconcile_job_name = f"process_{doc}_reconcile"
				if not is_job_running(reconcile_job_name):
					job = frappe.enqueue(
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
		log = frappe.db.get_all(
			"Process Payment Reconciliation Log", filters={"process_pr": doc}, as_list=1
		)
		if log:
			reconcile_log = frappe.get_doc("Process Payment Reconciliation Log", log[0][0])
			if reconcile_log.reconciled_entries != reconcile_log.total_allocations:
				try:
					pr = get_pr_instance(doc)

					# Just pass all invoices, no need to filter. They are only used for validations
					for x in reconcile_log.get("invoices"):
						pr.append("invoices", x.as_dict())

					# get current batch of unreconciled entries
					current_batch = split_allocations_into_batches(
						[x for x in reconcile_log.get("allocations") if x.reconciled == False]
					)

					# pass allocation to PR instance
					for x in current_batch:
						pr.append("allocation", x.as_dict())
						x.reconciled = True

					# then reconcile
					pr.reconcile(skip_job_check=True)

					reconcile_log.reconciled_entries = len(
						[x for x in reconcile_log.get("allocations") if x.reconciled == True]
					)
					reconcile_log.save()
				except Exception as err:
					# Update the parent doc about the exception
					frappe.db.rollback()

					traceback = frappe.get_traceback()
					if traceback:
						message = "Traceback: <br>" + traceback
						frappe.db.set_value(
							"Process Payment Reconciliation Log", reconcile_log.name, "error_log", message
						)
						frappe.db.set_value(
							"Process Payment Reconciliation",
							reconcile_log.process_pr,
							"error_log",
							message,
						)
					if (
						reconcile_log.reconciled_entries
						and reconcile_log.total_allocations
						and reconcile_log.reconciled_entries < reconcile_log.total_allocations
					):
						frappe.db.set_value(
							"Process Payment Reconciliation Log", reconcile_log.name, "status", "Partially Reconciled"
						)
						frappe.db.set_value(
							"Process Payment Reconciliation",
							reconcile_log.process_pr,
							"status",
							"Partially Reconciled",
						)
					else:
						frappe.db.set_value(
							"Process Payment Reconciliation Log", reconcile_log.name, "status", "Failed"
						)
						frappe.db.set_value(
							"Process Payment Reconciliation",
							reconcile_log.process_pr,
							"status",
							"Failed",
						)
				finally:
					reconcile_log.reload()
					if reconcile_log.reconciled_entries == reconcile_log.total_allocations:
						reconcile_log.reconciled = True
						reconcile_log.status = "Reconciled"
						reconcile_log.save()
						frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")
					else:
						# trigger next batch in job
						# generate reconcile job name
						batch = split_allocations_into_batches(
							[x for x in reconcile_log.get("allocations") if not x.reconciled]
						)
						if batch:
							start = batch[0].idx
							end = batch[-1].idx
							reconcile_job_name = f"process_{doc}_reconcile_{start}_{end}"
						else:
							reconcile_job_name = f"process_{doc}_reconcile"
						if not is_job_running(reconcile_job_name):
							job = frappe.enqueue(
								method="erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.reconcile",
								queue="long",
								timeout="3600",
								is_async=True,
								job_name=reconcile_job_name,
								enqueue_after_commit=True,
								doc=doc,
							)
			else:
				reconcile_log.reconciled = True
				reconcile_log.status = "Reconciled"
				reconcile_log.save()
				frappe.db.set_value("Process Payment Reconciliation", doc, "status", "Completed")


@frappe.whitelist()
def is_any_doc_running(for_filter: str | dict | None = None) -> tuple:
	running_doc = None
	if for_filter:
		if type(for_filter) == str:
			for_filter = frappe.json.loads(for_filter)
		running_doc = frappe.db.get_all(
			"Process Payment Reconciliation",
			filters={
				"docstatus": 1,
				"status": "Running",
				"company": for_filter.get("company"),
				"party_type": for_filter.get("party_type"),
				"party": for_filter.get("party"),
				"receivable_payable_account": for_filter.get("receivable_payable_account"),
			},
			as_list=1,
		)
	else:
		running_doc = frappe.db.get_all(
			"Process Payment Reconciliation", filters={"docstatus": 1, "status": "Running"}, as_list=1
		)
	return running_doc
