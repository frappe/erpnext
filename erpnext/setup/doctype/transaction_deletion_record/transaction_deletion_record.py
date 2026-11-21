# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.desk.notifications import clear_notifications
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import comma_and, create_batch, flt, get_link_to_form
from frappe.utils.background_jobs import get_job, is_job_enqueued

LEDGER_ENTRY_DOCTYPES = frozenset(
	(
		"GL Entry",
		"Payment Ledger Entry",
		"Stock Ledger Entry",
	)
)


class TransactionDeletionRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.transaction_deletion_record_details.transaction_deletion_record_details import (
			TransactionDeletionRecordDetails,
		)
		from erpnext.setup.doctype.transaction_deletion_record_item.transaction_deletion_record_item import (
			TransactionDeletionRecordItem,
		)

		amended_from: DF.Link | None
		clear_notifications: DF.Check
		company: DF.Link
		delete_bin_data: DF.Check
		delete_leads_and_addresses: DF.Check
		delete_transactions: DF.Check
		doctypes: DF.Table[TransactionDeletionRecordDetails]
		doctypes_to_be_ignored: DF.Table[TransactionDeletionRecordItem]
		error_log: DF.LongText | None
		initialize_doctypes_table: DF.Check
		process_in_single_transaction: DF.Check
		reset_company_default_values: DF.Check
		status: DF.Literal["Queued", "Running", "Failed", "Completed", "Cancelled"]
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.batch_size = 5000
		# Tasks are listed by their execution order
		self.task_to_internal_method_map = OrderedDict(
			{
				"Delete Leads and Addresses": "delete_lead_addresses",
				"Reset Company Values": "reset_company_values",
				"Clear Notifications": "delete_notifications",
				"Initialize Summary Table": "initialize_doctypes_to_be_deleted_table",
				"Delete Transactions": "delete_company_transactions",
				"Delete Bins": "delete_bins",
			}
		)

	def validate(self):
		frappe.only_for("System Manager")
		self.validate_doctypes_to_be_ignored()

	def validate_doctypes_to_be_ignored(self):
		doctypes_to_be_ignored_list = get_doctypes_to_be_ignored()
		for doctype in self.doctypes_to_be_ignored:
			if doctype.doctype_name not in doctypes_to_be_ignored_list:
				frappe.throw(
					_(
						"DocTypes should not be added manually to the 'Excluded DocTypes' table. You are only allowed to remove entries from it."
					),
					title=_("Not Allowed"),
				)

	def generate_job_name_for_task(self, task=None):
		method = self.task_to_internal_method_map[task]
		return f"{self.name}_{method}"

	def generate_job_name_for_next_tasks(self, task=None):
		job_names = []
		current_task_idx = list(self.task_to_internal_method_map).index(task)
		for idx, task in enumerate(self.task_to_internal_method_map.keys(), 0):
			# generate job_name for next tasks
			if idx > current_task_idx:
				job_names.append(self.generate_job_name_for_task(task))
		return job_names

	def generate_job_name_for_all_tasks(self):
		job_names = []
		for task in self.task_to_internal_method_map.keys():
			job_names.append(self.generate_job_name_for_task(task))
		return job_names

	def before_submit(self):
		if queued_docs := frappe.db.get_all(
			"Transaction Deletion Record",
			filters={"company": self.company, "status": ("in", ["Running", "Queued"]), "docstatus": 1},
			pluck="name",
		):
			frappe.throw(
				_(
					"Cannot enqueue multi docs for one company. {0} is already queued/running for company: {1}"
				).format(
					comma_and([get_link_to_form("Transaction Deletion Record", x) for x in queued_docs]),
					frappe.bold(self.company),
				)
			)

		if not self.doctypes_to_be_ignored:
			self.populate_doctypes_to_be_ignored_table()

	def reset_task_flags(self):
		self.clear_notifications = 0
		self.delete_bin_data = 0
		self.delete_leads_and_addresses = 0
		self.delete_transactions = 0
		self.initialize_doctypes_table = 0
		self.reset_company_default_values = 0

	def before_save(self):
		self.status = ""
		self.doctypes.clear()
		self.reset_task_flags()

	def on_submit(self):
		self.db_set("status", "Queued")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def enqueue_task(self, task: str | None = None):
		if task and task in self.task_to_internal_method_map:
			# make sure that none of next tasks are already running
			job_names = self.generate_job_name_for_next_tasks(task=task)
			self.validate_running_task_for_doc(job_names=job_names)

			# Generate Job Id to uniquely identify each task for this document
			job_id = self.generate_job_name_for_task(task)

			if self.process_in_single_transaction:
				self.execute_task(task_to_execute=task)
			else:
				frappe.enqueue(
					"frappe.utils.background_jobs.run_doc_method",
					doctype=self.doctype,
					name=self.name,
					doc_method="execute_task",
					job_id=job_id,
					queue="long",
					enqueue_after_commit=True,
					task_to_execute=task,
				)

	def execute_task(self, task_to_execute: str | None = None):
		if task_to_execute:
			method = self.task_to_internal_method_map[task_to_execute]
			if task := getattr(self, method, None):
				try:
					task()
				except Exception:
					if self.process_in_single_transaction:
						raise
					frappe.db.rollback()
					traceback = frappe.get_traceback(with_context=True)
					if traceback:
						message = "Traceback: <br>" + traceback
						frappe.db.set_value(self.doctype, self.name, "error_log", message)
					frappe.db.set_value(self.doctype, self.name, "status", "Failed")

	def delete_notifications(self):
		self.validate_doc_status()
		if not self.clear_notifications:
			clear_notifications()
			self.db_set("clear_notifications", 1)
		self.enqueue_task(task="Initialize Summary Table")

	def populate_doctypes_to_be_ignored_table(self):
		doctypes_to_be_ignored_list = get_doctypes_to_be_ignored()
		for doctype in doctypes_to_be_ignored_list:
			self.append("doctypes_to_be_ignored", {"doctype_name": doctype})

	def validate_running_task_for_doc(self, job_names: list | None = None):
		# at most only one task should be runnning
		running_tasks = []
		for x in job_names:
			if is_job_enqueued(x):
				running_tasks.append(get_job(x).get_id())

		if running_tasks:
			frappe.throw(
				_("{0} is already running for {1}").format(
					comma_and([get_link_to_form("RQ Job", x) for x in running_tasks]), self.name
				)
			)

	def validate_doc_status(self):
		if self.status != "Running":
			frappe.throw(
				_("{0} is not running. Cannot trigger events for this Document").format(
					get_link_to_form("Transaction Deletion Record", self.name)
				)
			)

	@frappe.whitelist(methods=["POST"])
	def start_deletion_tasks(self):
		self.reload()
		self.check_permission("write")
		if self.docstatus != 1 or self.status not in ("Queued", "Failed"):
			frappe.throw(
				_(
					"Only a submitted deletion with status Queued or Failed can be started. {0} is {1} with status {2}."
				).format(
					self.name,
					_({0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus]),
					_(self.status or "Not Set"),
				),
				title=_("Cannot Start Deletion"),
			)

		if self.status == "Failed":
			# A retry reruns every task, so the Bins are rebuilt after the transactions.
			self.before_submit()
			for fieldname in (
				"clear_notifications",
				"delete_bin_data",
				"delete_leads_and_addresses",
				"delete_transactions",
				"initialize_doctypes_table",
				"reset_company_default_values",
			):
				self.db_set(fieldname, 0)

		# This method is the entry point for the chain of events that follow
		self.db_set("status", "Running")
		self.enqueue_task(task="Delete Leads and Addresses")

	def delete_bins(self):
		"""Rebuild derived stock balances after deleting their source transactions."""
		self.validate_doc_status()
		if not self.delete_transactions:
			self.enqueue_task(task="Delete Leads and Addresses")
			return
		if not self.delete_bin_data:
			self.rebuild_bins()
			self.db_set("delete_bin_data", 1)
		self.db_set("status", "Completed")
		self.db_set("error_log", None)

	def rebuild_bins(self):
		from erpnext.stock.doctype.bin.bin import RECALCULATED_FIELDS
		from erpnext.stock.utils import get_bin

		bin_value_fields = (*RECALCULATED_FIELDS, "valuation_rate", "stock_value", "reserved_stock")
		warehouses = frappe.get_all("Warehouse", filters={"company": self.company}, pluck="name")
		if not warehouses:
			return

		item_warehouses = set()
		for doctype in ("Bin", "Stock Ledger Entry"):
			item_warehouses.update(
				tuple(row)
				for row in frappe.get_all(
					doctype,
					filters={"warehouse": ["in", warehouses]},
					fields=["item_code", "warehouse"],
					distinct=True,
					as_list=True,
				)
			)

		for item_code, warehouse in sorted(item_warehouses):
			bin = get_bin(item_code, warehouse)
			bin.recalculate_qty()
			bin.update_reserved_stock()
			self.set_bin_stock_value(bin)
			# An empty Bin equals a missing one; removing it keeps the Company deletable.
			# Filter on stored values so a concurrent stock update keeps its Bin.
			bin.reload()
			if not any(flt(bin.get(field)) for field in bin_value_fields):
				frappe.db.delete("Bin", {"name": bin.name, **dict.fromkeys(bin_value_fields, 0)})

	def set_bin_stock_value(self, bin):
		last_sle = (
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"item_code": bin.item_code, "warehouse": bin.warehouse, "is_cancelled": 0},
				["valuation_rate", "stock_value"],
				order_by="posting_date desc, posting_time desc, creation desc",
				as_dict=True,
			)
			or frappe._dict()
		)
		frappe.db.set_value(
			"Bin",
			bin.name,
			{
				"valuation_rate": flt(last_sle.valuation_rate),
				"stock_value": flt(last_sle.stock_value),
			},
			update_modified=False,
		)

	def delete_lead_addresses(self):
		"""Remove lead-only addresses and contacts while preserving shared records."""
		self.validate_doc_status()
		if not self.delete_leads_and_addresses:
			leads = frappe.db.get_all("Lead", filters={"company": self.company}, pluck="name")
			if leads:
				for doctype in ("Address", "Contact"):
					self.delete_lead_linked_records(doctype, leads)

				customer = qb.DocType("Customer")
				qb.update(customer).set(customer.lead_name, None).where(customer.lead_name.isin(leads)).run()

			self.db_set("delete_leads_and_addresses", 1)
		self.enqueue_task(task="Reset Company Values")

	def delete_lead_linked_records(self, doctype, leads):
		linked_records = frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": doctype, "link_doctype": "Lead", "link_name": ["in", leads]},
			pluck="parent",
		)
		if not linked_records:
			return

		dynamic_link = qb.DocType("Dynamic Link")
		other_links = (
			qb.from_(dynamic_link)
			.select(dynamic_link.parent)
			.where(
				(dynamic_link.parenttype == doctype)
				& dynamic_link.parent.isin(linked_records)
				& ((dynamic_link.link_doctype != "Lead") | dynamic_link.link_name.notin(leads))
			)
		)
		parent = qb.DocType(doctype)
		exclusive_records = (
			qb.from_(parent)
			.select(parent.name)
			.where(parent.name.isin(linked_records) & parent.name.notin(other_links))
			.run(pluck=True)
		)
		if exclusive_records:
			self.delete_version_log(doctype, exclusive_records)
			self.delete_communications(doctype, exclusive_records)
			self.delete_comments(doctype, exclusive_records)
			self.delete_document_references(doctype, exclusive_records)
			self.unlink_attachments(doctype, exclusive_records)
			self.delete_child_tables(doctype, exclusive_records)
			frappe.db.delete(doctype, {"name": ["in", exclusive_records]})
		frappe.db.delete(
			"Dynamic Link",
			{
				"parenttype": doctype,
				"link_doctype": "Lead",
				"link_name": ["in", leads],
			},
		)

	def reset_company_values(self):
		self.validate_doc_status()
		if not self.reset_company_default_values:
			frappe.db.set_value(
				"Company",
				self.company,
				{
					"total_monthly_sales": 0,
					"sales_monthly_history": None,
					"transactions_annual_history": None,
				},
			)
			frappe.clear_document_cache("Company", self.company)
			self.db_set("reset_company_default_values", 1)
		self.enqueue_task(task="Clear Notifications")

	def initialize_doctypes_to_be_deleted_table(self):
		self.validate_doc_status()
		if not self.initialize_doctypes_table:
			doctypes_to_be_ignored_list = self.get_doctypes_to_be_ignored_list()
			docfields = self.get_doctypes_with_company_field(doctypes_to_be_ignored_list)
			tables = self.get_all_child_doctypes()
			for docfield in docfields:
				if docfield["parent"] != self.doctype:
					no_of_docs = self.get_number_of_docs_linked_with_specified_company(
						docfield["parent"], docfield["fieldname"]
					)
					if no_of_docs > 0:
						existing = next(
							(
								row
								for row in self.doctypes
								if row.doctype_name == docfield["parent"]
								and row.docfield_name == docfield["fieldname"]
							),
							None,
						)
						if existing:
							existing.db_set("done", 0)
						else:
							self.populate_doctypes_table(tables, docfield["parent"], docfield["fieldname"], 0)
			self.db_set("initialize_doctypes_table", 1)
		self.enqueue_task(task="Delete Transactions")

	def delete_company_transactions(self):
		self.validate_doc_status()
		if not self.delete_transactions:
			doctypes_to_be_ignored_list = self.get_doctypes_to_be_ignored_list()
			self.get_doctypes_with_company_field(doctypes_to_be_ignored_list)

			self.get_all_child_doctypes()
			for docfield in self.doctypes:
				if docfield.doctype_name != self.doctype and not docfield.done:
					no_of_docs = self.get_number_of_docs_linked_with_specified_company(
						docfield.doctype_name, docfield.docfield_name
					)
					if no_of_docs > 0:
						reference_docs = frappe.get_all(
							docfield.doctype_name,
							filters={docfield.docfield_name: self.company},
							order_by="name asc",
							limit=self.batch_size,
						)
						reference_doc_names = [r.name for r in reference_docs]
						batch_nos = self.get_affected_batches(docfield.doctype_name, reference_doc_names)

						self.delete_version_log(docfield.doctype_name, reference_doc_names)
						self.delete_communications(docfield.doctype_name, reference_doc_names)
						self.delete_comments(docfield.doctype_name, reference_doc_names)
						self.delete_document_references(docfield.doctype_name, reference_doc_names)
						self.unlink_attachments(docfield.doctype_name, reference_doc_names)
						self.delete_child_tables(docfield.doctype_name, reference_doc_names)
						self.delete_docs_linked_with_specified_company(
							docfield.doctype_name, reference_doc_names
						)
						self.recalculate_batch_quantities(batch_nos)
						processed = int(docfield.no_of_docs) + len(reference_doc_names)
						frappe.db.set_value(docfield.doctype, docfield.name, "no_of_docs", processed)
					else:
						frappe.db.set_value(docfield.doctype, docfield.name, "done", 1)

			pending_doctypes = frappe.db.get_all(
				"Transaction Deletion Record Details",
				filters={"parent": self.name, "done": 0},
				pluck="doctype_name",
			)
			if pending_doctypes:
				# as method is enqueued after commit, calling itself will not make validate_doc_status to throw
				# recursively call this task to delete all transactions
				self.enqueue_task(task="Delete Transactions")
			else:
				self.db_set("delete_transactions", 1)
				self.db_set("delete_bin_data", 0)
				self.enqueue_task(task="Delete Bins")

	def get_doctypes_to_be_ignored_list(self):
		doctypes_to_be_ignored_list = frappe.get_all(
			"DocType", or_filters=[["issingle", "=", 1], ["is_virtual", "=", 1]], pluck="name"
		)
		for doctype in self.doctypes_to_be_ignored:
			doctypes_to_be_ignored_list.append(doctype.doctype_name)

		return doctypes_to_be_ignored_list

	def get_doctypes_with_company_field(self, doctypes_to_be_ignored_list):
		"""Return the DocTypes owned by a Company through a field named `company`.

		Secondary Company links (for example `represents_company`) and DocTypes whose
		owning field is ambiguous are not used for automatic deletion."""
		filters = {"fieldtype": "Link", "options": "Company"}
		company_fields = frappe.get_all(
			"DocField",
			filters={**filters, "parent": ["not in", doctypes_to_be_ignored_list]},
			fields=["parent", "fieldname"],
		)
		company_fields.extend(
			frappe.get_all(
				"Custom Field",
				filters={**filters, "dt": ["not in", doctypes_to_be_ignored_list]},
				fields=["dt as parent", "fieldname"],
			)
		)

		owned_doctypes = list(
			dict.fromkeys(row.parent for row in company_fields if row.fieldname == "company")
		)
		return [frappe._dict(parent=doctype, fieldname="company") for doctype in owned_doctypes]

	def get_all_child_doctypes(self):
		return frappe.get_all("DocType", filters={"istable": 1}, pluck="name")

	def get_number_of_docs_linked_with_specified_company(self, doctype, company_fieldname):
		return frappe.db.count(doctype, {company_fieldname: self.company})

	def populate_doctypes_table(self, tables, doctype, fieldname, no_of_docs):
		self.flags.ignore_validate_update_after_submit = True
		if doctype not in tables:
			self.append(
				"doctypes", {"doctype_name": doctype, "docfield_name": fieldname, "no_of_docs": no_of_docs}
			)
		self.save(ignore_permissions=True)

	def delete_child_tables(self, doctype, reference_doc_names):
		child_tables = frappe.get_all(
			"DocField", filters={"fieldtype": "Table", "parent": doctype}, pluck="options"
		)

		for table in child_tables:
			frappe.db.delete(table, {"parenttype": doctype, "parent": ["in", reference_doc_names]})

	def delete_docs_linked_with_specified_company(self, doctype, reference_doc_names):
		frappe.db.delete(doctype, {"name": ("in", reference_doc_names)})

	def get_affected_batches(self, doctype, docnames):
		batches = set()
		if doctype == "Stock Ledger Entry":
			entries = frappe.get_all(
				doctype, filters={"name": ["in", docnames]}, fields=["batch_no", "serial_and_batch_bundle"]
			)
			batches.update(row.batch_no for row in entries if row.batch_no)
			bundles = [row.serial_and_batch_bundle for row in entries if row.serial_and_batch_bundle]
		elif doctype == "Serial and Batch Bundle":
			bundles = docnames
		else:
			return batches
		if bundles:
			batches.update(
				frappe.get_all(
					"Serial and Batch Entry",
					filters={
						"parenttype": "Serial and Batch Bundle",
						"parent": ["in", bundles],
						"batch_no": ["is", "set"],
					},
					pluck="batch_no",
				)
			)
		return batches

	def recalculate_batch_quantities(self, batch_nos):
		if not batch_nos:
			return
		sle = qb.DocType("Stock Ledger Entry")
		entry = qb.DocType("Serial and Batch Entry")
		legacy_quantities = (
			qb.from_(sle)
			.select(sle.batch_no, Sum(sle.actual_qty).as_("qty"))
			.where(
				(sle.is_cancelled == 0)
				& sle.batch_no.isin(batch_nos)
				& (sle.serial_and_batch_bundle.isnull() | (sle.serial_and_batch_bundle == ""))
			)
			.groupby(sle.batch_no)
		)
		bundle_quantities = (
			qb.from_(entry)
			.join(sle)
			.on(entry.parent == sle.serial_and_batch_bundle)
			.select(entry.batch_no, Sum(entry.qty).as_("qty"))
			.where(
				(sle.is_cancelled == 0)
				& (entry.parenttype == "Serial and Batch Bundle")
				& entry.batch_no.isin(batch_nos)
			)
			.groupby(entry.batch_no)
		)
		quantities = dict.fromkeys(batch_nos, 0)
		for query in (legacy_quantities, bundle_quantities):
			for row in query.run(as_dict=True):
				quantities[row.batch_no] += row.qty
		for batch_no, qty in quantities.items():
			frappe.db.set_value("Batch", batch_no, "batch_qty", qty, update_modified=False)

	def delete_document_references(self, doctype, docnames):
		for reference_doctype, doctype_field, name_field in (
			("ToDo", "reference_type", "reference_name"),
			("DocShare", "share_doctype", "share_name"),
			("Tag Link", "document_type", "document_name"),
			("Document Follow", "ref_doctype", "ref_docname"),
			("Notification Log", "document_type", "document_name"),
		):
			frappe.db.delete(reference_doctype, {doctype_field: doctype, name_field: ["in", docnames]})

	def delete_version_log(self, doctype, docnames):
		versions = qb.DocType("Version")
		qb.from_(versions).delete().where(
			(versions.ref_doctype == doctype) & (versions.docname.isin(docnames))
		).run()

	def delete_communications(self, doctype, reference_doc_names):
		communications = frappe.get_all(
			"Communication",
			filters={"reference_doctype": doctype, "reference_name": ["in", reference_doc_names]},
		)
		communication_names = [c.name for c in communications]

		if not communication_names:
			return

		for batch in create_batch(communication_names, self.batch_size):
			frappe.delete_doc("Communication", batch, ignore_permissions=True)

	def delete_comments(self, doctype, reference_doc_names):
		if reference_doc_names:
			comment = qb.DocType("Comment")
			qb.from_(comment).delete().where(
				(comment.reference_doctype == doctype) & (comment.reference_name.isin(reference_doc_names))
			).run()

	def unlink_attachments(self, doctype, reference_doc_names):
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": ["in", reference_doc_names]},
		)
		file_names = [c.name for c in files]

		if not file_names:
			return

		folder = frappe.get_doc(
			{"doctype": "File", "file_name": "Transaction Deletion Review", "is_folder": 1, "folder": "Home"}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
		file = qb.DocType("File")

		for batch in create_batch(file_names, self.batch_size):
			qb.update(file).set(file.attached_to_doctype, None).set(file.attached_to_name, None).set(
				file.attached_to_field, None
			).set(file.folder, folder.name).where(file.name.isin(batch)).run()
		self.add_comment(
			"Info",
			_("Detached attachments are retained in {0} for review.").format(
				get_link_to_form("File", folder.name)
			),
		)


@frappe.whitelist()
def get_doctypes_to_be_ignored():
	doctypes_to_be_ignored = [
		"Account",
		"Cost Center",
		"Cost Center Allocation",
		"Warehouse",
		"Bin",
		"Budget",
		"Party Account",
		"Employee",
		"Sales Taxes and Charges Template",
		"Purchase Taxes and Charges Template",
		"POS Profile",
		"BOM",
		"Company",
		"Bank Account",
		"Item Tax Template",
		"Mode of Payment",
		"Mode of Payment Account",
		"Item Default",
		"Customer",
		"Supplier",
		"Department",
		"Accounting Dimension Filter",
		"Accounting Period",
		"Asset Maintenance Team",
		"Authorization Rule",
		"Dunning Type",
		"Email Digest",
		"Journal Entry Template",
		"Loyalty Program",
		"Payment Gateway Account",
		"Plant Floor",
		"Pricing Rule",
		"Project",
		"Promotional Scheme",
		"Putaway Rule",
		"Shareholder",
		"Shipping Rule",
		"South Africa VAT Settings",
		"Tax Rule",
		"UAE VAT Settings",
		"Vehicle",
	]

	doctypes_to_be_ignored.extend(frappe.get_hooks("company_data_to_be_ignored") or [])

	return doctypes_to_be_ignored


@frappe.whitelist()
def is_deletion_doc_running(company: str | None = None, err_msg: str | None = None):
	if not company:
		return

	running_deletion_job = frappe.db.get_value(
		"Transaction Deletion Record",
		{"docstatus": 1, "company": company, "status": "Running"},
		"name",
	)

	if not running_deletion_job:
		return

	frappe.throw(
		title=_("Deletion in Progress!"),
		msg=_("Transaction Deletion Document: {0} is running for this Company. {1}").format(
			get_link_to_form("Transaction Deletion Record", running_deletion_job), err_msg or ""
		),
	)


def check_for_running_deletion_job(doc, method=None):
	# Check if DocType has 'company' field
	if doc.doctype in LEDGER_ENTRY_DOCTYPES or not doc.meta.has_field("company"):
		return

	is_deletion_doc_running(
		doc.company, _("Cannot make any transactions until the deletion job is completed")
	)
