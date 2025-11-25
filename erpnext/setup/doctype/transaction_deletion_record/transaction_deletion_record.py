# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.desk.notifications import clear_notifications
from frappe.model.document import Document
from frappe.utils import cint, comma_and, create_batch, get_link_to_form
from frappe.utils.background_jobs import get_job, is_job_enqueued
from frappe.utils.caching import request_cache

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
				"Delete Bins": "delete_bins",
				"Delete Leads and Addresses": "delete_lead_addresses",
				"Reset Company Values": "reset_company_values",
				"Clear Notifications": "delete_notifications",
				"Initialize Summary Table": "initialize_doctypes_to_be_deleted_table",
				"Delete Transactions": "delete_company_transactions",
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

	@frappe.whitelist()
	def start_deletion_tasks(self):
		# This method is the entry point for the chain of events that follow
		self.db_set("status", "Running")
		self.enqueue_task(task="Delete Bins")

	def delete_bins(self):
		self.validate_doc_status()
		if not self.delete_bin_data:
			frappe.db.sql(
				"""delete from `tabBin` where warehouse in
					(select name from tabWarehouse where company=%s)""",
				self.company,
			)
			self.db_set("delete_bin_data", 1)
		self.enqueue_task(task="Delete Leads and Addresses")

	def delete_lead_addresses(self):
		"""Delete addresses to which leads are linked"""
		self.validate_doc_status()
		if not self.delete_leads_and_addresses:
			leads = frappe.db.get_all("Lead", filters={"company": self.company}, pluck="name")
			addresses = []
			if leads:
				addresses = frappe.db.get_all(
					"Dynamic Link", filters={"link_name": ("in", leads)}, pluck="parent"
				)
				if addresses:
					addresses = ["%s" % frappe.db.escape(addr) for addr in addresses]

					address = qb.DocType("Address")
					dl1 = qb.DocType("Dynamic Link")
					dl2 = qb.DocType("Dynamic Link")

					qb.from_(address).delete().where(
						(address.name.isin(addresses))
						& (
							address.name.notin(
								qb.from_(dl1)
								.join(dl2)
								.on((dl1.parent == dl2.parent) & (dl1.link_doctype != dl2.link_doctype))
								.select(dl1.parent)
								.distinct()
							)
						)
					).run()

					dynamic_link = qb.DocType("Dynamic Link")
					qb.from_(dynamic_link).delete().where(
						(dynamic_link.link_doctype == "Lead")
						& (dynamic_link.parenttype == "Address")
						& (dynamic_link.link_name.isin(leads))
					).run()

				customer = qb.DocType("Customer")
				qb.update(customer).set(customer.lead_name, None).where(customer.lead_name.isin(leads)).run()

			self.db_set("delete_leads_and_addresses", 1)
		self.enqueue_task(task="Reset Company Values")

	def reset_company_values(self):
		self.validate_doc_status()
		if not self.reset_company_default_values:
			company_obj = frappe.get_doc("Company", self.company)
			company_obj.total_monthly_sales = 0
			company_obj.sales_monthly_history = None
			company_obj.save()
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
						# Initialize
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
							limit=self.batch_size,
						)
						reference_doc_names = [r.name for r in reference_docs]

						self.delete_version_log(docfield.doctype_name, reference_doc_names)
						self.delete_communications(docfield.doctype_name, reference_doc_names)
						self.delete_comments(docfield.doctype_name, reference_doc_names)
						self.unlink_attachments(docfield.doctype_name, reference_doc_names)
						self.delete_child_tables(docfield.doctype_name, reference_doc_names)
						self.delete_docs_linked_with_specified_company(
							docfield.doctype_name, reference_doc_names
						)
						processed = int(docfield.no_of_docs) + len(reference_doc_names)
						frappe.db.set_value(docfield.doctype, docfield.name, "no_of_docs", processed)
					else:
						# reset naming series
						naming_series = frappe.db.get_value("DocType", docfield.doctype_name, "autoname")
						if naming_series:
							if "#" in naming_series:
								self.update_naming_series(naming_series, docfield.doctype_name)
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
				self.db_set("status", "Completed")
				self.db_set("delete_transactions", 1)
				self.db_set("error_log", None)

	def get_doctypes_to_be_ignored_list(self):
		singles = frappe.get_all("DocType", filters={"issingle": 1}, pluck="name")
		doctypes_to_be_ignored_list = singles
		for doctype in self.doctypes_to_be_ignored:
			doctypes_to_be_ignored_list.append(doctype.doctype_name)

		return doctypes_to_be_ignored_list

	def get_doctypes_with_company_field(self, doctypes_to_be_ignored_list):
		docfields = frappe.get_all(
			"DocField",
			filters={
				"fieldtype": "Link",
				"options": "Company",
				"parent": ["not in", doctypes_to_be_ignored_list],
			},
			fields=["parent", "fieldname"],
		)

		return docfields

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
			frappe.db.delete(table, {"parent": ["in", reference_doc_names]})

	def delete_docs_linked_with_specified_company(self, doctype, reference_doc_names):
		frappe.db.delete(doctype, {"name": ("in", reference_doc_names)})

	def update_naming_series(self, naming_series, doctype_name):
		if "." in naming_series:
			prefix, hashes = naming_series.rsplit(".", 1)
		else:
			prefix, hashes = naming_series.rsplit("{", 1)
		last = frappe.db.sql(
			f"""select max(name) from `tab{doctype_name}`
						where name like %s""",
			prefix + "%",
		)
		if last and last[0][0]:
			last = cint(last[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.sql("""update `tabSeries` set current = %s where name=%s""", (last, prefix))

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

		file = qb.DocType("File")

		for batch in create_batch(file_names, self.batch_size):
			qb.update(file).set(file.attached_to_doctype, None).set(file.attached_to_name, None).where(
				file.name.isin(batch)
			).run()


@frappe.whitelist()
def get_doctypes_to_be_ignored():
	doctypes_to_be_ignored = [
		"Account",
		"Cost Center",
		"Warehouse",
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
	]

	doctypes_to_be_ignored.extend(frappe.get_hooks("company_data_to_be_ignored") or [])

	return doctypes_to_be_ignored


@frappe.whitelist()
@request_cache
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
