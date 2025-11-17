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

PROTECTED_CORE_DOCTYPES = frozenset(
	(
		# Core Meta
		"DocType",
		"DocField",
		"Custom Field",
		"Property Setter",
		# User & Permissions
		"User",
		"Role",
		"Has Role",
		"User Permission",
		# System Configuration
		"Module Def",
		"Workflow",
		"Workflow State",
	)
)


def get_protected_doctypes():
	"""Get list of protected DocTypes that cannot be deleted"""
	protected = []

	# Add core protected DocTypes (only if they exist)
	for doctype in PROTECTED_CORE_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			protected.append(doctype)

	# Add all Single DocTypes
	singles = frappe.get_all("DocType", filters={"issingle": 1}, pluck="name")
	protected.extend(singles)

	return protected


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
		from erpnext.setup.doctype.transaction_deletion_record_to_delete.transaction_deletion_record_to_delete import (
			TransactionDeletionRecordToDelete,
		)

		amended_from: DF.Link | None
		clear_notifications: DF.Check
		company: DF.Link
		delete_bin_data: DF.Check
		delete_leads_and_addresses: DF.Check
		delete_transactions: DF.Check
		doctypes: DF.Table[TransactionDeletionRecordDetails]
		doctypes_to_be_ignored: DF.Table[TransactionDeletionRecordItem]
		doctypes_to_delete: DF.Table[TransactionDeletionRecordToDelete]
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

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def validate(self):
		frappe.only_for("System Manager")
		self.validate_doctypes_to_be_ignored()
		self.validate_to_delete_list()

	def validate_doctypes_to_be_ignored(self):
		"""Allow users to freely edit the exclusion list - protected DocTypes are handled during generation"""
		# Users can freely edit - protected DocTypes are automatically excluded during generation
		pass

	def validate_to_delete_list(self):
		"""Ensure no protected DocTypes in to-delete list and all exist"""
		if not self.doctypes_to_delete:
			return

		protected = get_protected_doctypes()

		for item in self.doctypes_to_delete:
			# Check existence
			if not frappe.db.exists("DocType", item.doctype_name):
				frappe.throw(_("DocType {0} does not exist").format(item.doctype_name))

			# Check protection (if in list, it will be deleted)
			if item.doctype_name in protected:
				frappe.throw(
					_("Cannot delete protected core DocType: {0}").format(item.doctype_name),
					title=_("Protected DocType"),
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

		# Require To Delete list for new workflow (backwards compatible)
		if not self.doctypes_to_delete and not self.doctypes_to_be_ignored:
			frappe.throw(_("Please generate To Delete list before submitting"))

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
		# Automatically start deletion after submit
		self.start_deletion_tasks()

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def generate_to_delete_list(self):
		"""Generate To Delete list from all DocTypes minus exclusions"""
		self.doctypes_to_delete = []

		# Get exclusions (user-specified + protected)
		excluded = [d.doctype_name for d in self.doctypes_to_be_ignored]
		excluded.extend(get_protected_doctypes())

		# Get all DocTypes with company field
		docfields = frappe.get_all(
			"DocField",
			filters={"fieldtype": "Link", "options": "Company"},
			fields=["parent", "fieldname"],
		)

		# Create a dict to group by parent for deduplication
		parent_to_fieldname = {}
		for docfield in docfields:
			if docfield["parent"] not in parent_to_fieldname:
				parent_to_fieldname[docfield["parent"]] = docfield["fieldname"]

		for doctype_name, company_fieldname in parent_to_fieldname.items():
			if doctype_name not in excluded and doctype_name != self.doctype:
				# Skip child tables (they're deleted automatically with their parents)
				is_child_table = frappe.db.get_value("DocType", doctype_name, "istable")
				if is_child_table:
					continue

				doc_count = self.get_number_of_docs_linked_with_specified_company(
					doctype_name, company_fieldname
				)

				# Get child DocTypes for this parent
				child_tables = frappe.get_all(
					"DocField", filters={"parent": doctype_name, "fieldtype": "Table"}, pluck="options"
				)
				child_doctypes_str = ", ".join(child_tables) if child_tables else ""

				self.append(
					"doctypes_to_delete",
					{
						"doctype_name": doctype_name,
						"document_count": doc_count,
						"child_doctypes": child_doctypes_str,
					},
				)

		self.save()
		return {"count": len(self.doctypes_to_delete)}

	@frappe.whitelist()
	def populate_doctype_details(self, doctype_name, company=None):
		"""Populate child DocTypes and document count for a given DocType"""
		if not doctype_name:
			return {}

		# Check if it's a child table (should not be added directly)
		is_child_table = frappe.db.get_value("DocType", doctype_name, "istable")
		if is_child_table:
			return {
				"child_doctypes": "",
				"document_count": 0,
				"error": _("{0} is a child table and will be deleted automatically with its parent").format(
					doctype_name
				),
			}

		try:
			# Use provided company or fall back to self.company
			company_to_use = company or self.company

			# Get child tables
			child_tables = frappe.get_all(
				"DocField", filters={"parent": doctype_name, "fieldtype": "Table"}, pluck="options"
			)
			child_doctypes_str = ", ".join(child_tables) if child_tables else ""

			# Only filter by company if field is specifically named "company"
			has_company_field = frappe.db.exists(
				"DocField",
				{"parent": doctype_name, "fieldname": "company", "fieldtype": "Link", "options": "Company"},
			)

			# Get document count
			if has_company_field and company_to_use:
				# Filter by company only if field is named "company"
				doc_count = frappe.db.count(doctype_name, filters={"company": company_to_use})
			else:
				# No company field or field not named "company" - get total count
				doc_count = frappe.db.count(doctype_name)

			return {
				"child_doctypes": child_doctypes_str,
				"document_count": doc_count,
			}
		except Exception as e:
			frappe.log_error(f"Error in populate_doctype_details for {doctype_name}: {e!s}")
			# Return at least the doctype name on error
			return {
				"child_doctypes": "",
				"document_count": 0,
				"error": str(e),
			}

	@frappe.whitelist()
	def export_to_delete_template_method(self):
		"""Export To Delete list as CSV template"""
		if not self.doctypes_to_delete:
			frappe.throw(_("Generate To Delete list first"))

		import csv
		from io import StringIO

		output = StringIO()
		writer = csv.writer(output)
		writer.writerow(["doctype_name", "child_doctypes"])

		for item in self.doctypes_to_delete:
			writer.writerow([item.doctype_name, item.child_doctypes or ""])

		csv_content = output.getvalue()

		# Use standard Frappe CSV response pattern
		frappe.response["result"] = csv_content
		frappe.response["type"] = "csv"
		frappe.response[
			"doctype"
		] = f"deletion_template_{self.company}_{frappe.utils.now_datetime().strftime('%Y%m%d')}"

	@frappe.whitelist()
	def import_to_delete_template_method(self, csv_content):
		"""Import CSV template and regenerate counts"""
		import csv
		from io import StringIO

		self.doctypes_to_delete = []
		protected = get_protected_doctypes()

		reader = csv.DictReader(StringIO(csv_content))
		imported_count = 0

		for row in reader:
			doctype_name = row.get("doctype_name", "").strip()
			child_doctypes = row.get("child_doctypes", "").strip()

			if not doctype_name:
				continue

			if doctype_name in protected:
				frappe.msgprint(_("Skipping protected DocType: {0}").format(doctype_name))
				continue

			if not frappe.db.exists("DocType", doctype_name):
				frappe.msgprint(_("DocType not found: {0}").format(doctype_name))
				continue

			# Get fresh count
			company_field = frappe.db.get_value(
				"DocField",
				{"parent": doctype_name, "fieldtype": "Link", "options": "Company"},
				"fieldname",
			)

			if company_field:
				doc_count = self.get_number_of_docs_linked_with_specified_company(doctype_name, company_field)
			else:
				doc_count = frappe.db.count(doctype_name)

			self.append(
				"doctypes_to_delete",
				{
					"doctype_name": doctype_name,
					"document_count": doc_count,
					"child_doctypes": child_doctypes,
				},
			)
			imported_count += 1

		self.save()
		return {"imported": imported_count}

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
		"""Initialize deletion table from To Delete list or fall back to original logic"""
		self.validate_doc_status()
		if not self.initialize_doctypes_table:
			# Use To Delete list if available (new behavior)
			if self.doctypes_to_delete:
				tables = self.get_all_child_doctypes()

				for to_delete_item in self.doctypes_to_delete:
					if to_delete_item.document_count > 0:
						# Add parent DocType only - child tables are handled automatically
						# by delete_child_tables() when the parent is deleted
						# Only use "company" field if it exists, otherwise pass None
						has_company_field = frappe.db.exists(
							"DocField",
							{
								"parent": to_delete_item.doctype_name,
								"fieldname": "company",
								"fieldtype": "Link",
								"options": "Company",
							},
						)
						self.populate_doctypes_table(
							tables, to_delete_item.doctype_name, "company" if has_company_field else None, 0
						)
			else:
				# Fallback to original logic (backwards compatibility)
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
					# Only filter by company if field is named "company"
					if docfield.docfield_name == "company":
						# Filter by company
						no_of_docs = self.get_number_of_docs_linked_with_specified_company(
							docfield.doctype_name, docfield.docfield_name
						)
					else:
						# No company field or field not named "company" - count all
						no_of_docs = frappe.db.count(docfield.doctype_name)

					if no_of_docs > 0:
						# Get reference docs - filter by company only if field is "company"
						if docfield.docfield_name == "company":
							reference_docs = frappe.get_all(
								docfield.doctype_name,
								filters={"company": self.company},
								limit=self.batch_size,
							)
						else:
							# No company field - get all docs (don't use pluck to keep dict-like objects)
							reference_docs = frappe.get_all(
								docfield.doctype_name, fields=["name"], limit=self.batch_size
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

						# Also mark as deleted in the "To Delete" table
						to_delete_row = frappe.db.get_value(
							"Transaction Deletion Record To Delete",
							{"parent": self.name, "doctype_name": docfield.doctype_name},
							"name",
						)
						if to_delete_row:
							frappe.db.set_value(
								"Transaction Deletion Record To Delete", to_delete_row, "deleted", 1
							)

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
		doctypes_to_be_ignored_list = frappe.get_all(
			"DocType", or_filters=[["issingle", "=", 1], ["is_virtual", "=", 1]], pluck="name"
		)
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

	def get_company_field(self, doctype_name):
		"""Get company field name for a DocType"""
		return frappe.db.get_value(
			"DocField",
			{"parent": doctype_name, "fieldtype": "Link", "options": "Company"},
			"fieldname",
		)

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
def export_to_delete_template(name):
	"""Module-level export function for direct URL access"""
	doc = frappe.get_doc("Transaction Deletion Record", name)
	doc.check_permission("read")
	return doc.export_to_delete_template_method()


@frappe.whitelist()
def process_import_template(transaction_deletion_record_name, file_url):
	"""Process uploaded CSV template file"""
	doc = frappe.get_doc("Transaction Deletion Record", transaction_deletion_record_name)
	doc.check_permission("write")

	# Get file doc and read content using standard Frappe pattern
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_path = file_doc.get_full_path()

	with open(file_path, encoding="utf-8") as f:
		csv_content = f.read()

	return doc.import_to_delete_template_method(csv_content)


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
