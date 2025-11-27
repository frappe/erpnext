# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.desk.notifications import clear_notifications
from frappe.model.document import Document
from frappe.query_builder.functions import Max
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

DELETION_CACHE_TTL = 4 * 60 * 60  # 4 hours in seconds

PROTECTED_CORE_DOCTYPES = frozenset(
	(
		# Core Meta
		"DocType",
		"DocField",
		"Custom Field",
		"Property Setter",
		"DocPerm",
		"Custom DocPerm",
		# User & Permissions
		"User",
		"Role",
		"Has Role",
		"User Permission",
		"User Type",
		# System Configuration
		"Module Def",
		"Workflow",
		"Workflow State",
		"System Settings",
		# Critical System DocTypes
		"File",
		"Version",
		"Activity Log",
		"Error Log",
		"Scheduled Job Type",
		"Scheduled Job Log",
		"Server Script",
		"Client Script",
		"Data Import",
		"Data Export",
		"Report",
		"Print Format",
		"Email Template",
		"Assignment Rule",
		"Workspace",
		"Dashboard",
		"Access Log",
		# Transaction Deletion
		"Transaction Deletion Record",
		"Company",
	)
)


@frappe.whitelist()
def get_protected_doctypes():
	"""Get list of protected DocTypes that cannot be deleted (whitelisted for frontend)"""
	frappe.only_for("System Manager")
	return _get_protected_doctypes_internal()


@frappe.whitelist()
def get_company_link_fields(doctype_name):
	"""Get all Company Link field names for a DocType (whitelisted for frontend autocomplete)

	Args:
	        doctype_name: The DocType to check

	Returns:
	        list: List of field names that link to Company DocType, ordered by field index
	"""
	frappe.only_for("System Manager")
	if not doctype_name or not frappe.db.exists("DocType", doctype_name):
		return []

	return frappe.get_all(
		"DocField",
		filters={"parent": doctype_name, "fieldtype": "Link", "options": "Company"},
		pluck="fieldname",
		order_by="idx",
	)


def _get_protected_doctypes_internal():
	"""Internal method to get protected doctypes"""
	protected = []

	for doctype in PROTECTED_CORE_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			protected.append(doctype)

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
		clear_notifications_status: DF.Literal["Pending", "Completed", "Skipped"]
		company: DF.Link
		delete_bin_data_status: DF.Literal["Pending", "Completed", "Skipped"]
		delete_leads_and_addresses_status: DF.Literal["Pending", "Completed", "Skipped"]
		delete_transactions_status: DF.Literal["Pending", "Completed", "Skipped"]
		doctypes: DF.Table[TransactionDeletionRecordDetails]
		doctypes_to_be_ignored: DF.Table[TransactionDeletionRecordItem]
		doctypes_to_delete: DF.Table[TransactionDeletionRecordToDelete]
		error_log: DF.LongText | None
		initialize_doctypes_table_status: DF.Literal["Pending", "Completed", "Skipped"]
		process_in_single_transaction: DF.Check
		reset_company_default_values_status: DF.Literal["Pending", "Completed", "Skipped"]
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
		self.validate_to_delete_list()

	def validate_to_delete_list(self):
		"""Validate To Delete list: existence, protection status, child table exclusion, duplicates"""
		if not self.doctypes_to_delete:
			return

		protected = _get_protected_doctypes_internal()
		seen_combinations = set()

		for item in self.doctypes_to_delete:
			if not frappe.db.exists("DocType", item.doctype_name):
				frappe.throw(_("DocType {0} does not exist").format(item.doctype_name))

			# Check for duplicates using composite key
			composite_key = (item.doctype_name, item.company_field or None)
			if composite_key in seen_combinations:
				field_desc = f" with company field '{item.company_field}'" if item.company_field else ""
				frappe.throw(
					_("Duplicate entry: {0}{1}").format(item.doctype_name, field_desc),
					title=_("Duplicate DocType"),
				)
			seen_combinations.add(composite_key)

			# Validate protected DocTypes
			if item.doctype_name in protected:
				frappe.throw(
					_("Cannot delete protected core DocType: {0}").format(item.doctype_name),
					title=_("Protected DocType"),
				)

			is_child_table = frappe.db.get_value("DocType", item.doctype_name, "istable")
			if is_child_table:
				frappe.throw(
					_(
						"Cannot add child table {0} to deletion list. Child tables are automatically deleted with their parent DocTypes."
					).format(item.doctype_name),
					title=_("Child Table Not Allowed"),
				)

			is_virtual = frappe.db.get_value("DocType", item.doctype_name, "is_virtual")
			if is_virtual:
				frappe.throw(
					_(
						"Cannot delete virtual DocType: {0}. Virtual DocTypes do not have database tables."
					).format(item.doctype_name),
					title=_("Virtual DocType"),
				)

			# Validate company_field if specified
			if item.company_field:
				valid_company_fields = self._get_company_link_fields(item.doctype_name)
				if item.company_field not in valid_company_fields:
					frappe.throw(
						_("Field '{0}' is not a valid Company link field for DocType {1}").format(
							item.company_field, item.doctype_name
						),
						title=_("Invalid Company Field"),
					)

	def _is_any_doctype_in_deletion_list(self, doctypes_list):
		"""Check if any DocType from the list is in the To Delete list"""
		if not self.doctypes_to_delete:
			return False

		deletion_doctypes = {d.doctype_name for d in self.doctypes_to_delete}
		return any(doctype in deletion_doctypes for doctype in doctypes_list)

	def generate_job_name_for_task(self, task=None):
		"""Generate unique job name for a specific task"""
		method = self.task_to_internal_method_map[task]
		return f"{self.name}_{method}"

	def generate_job_name_for_next_tasks(self, task=None):
		"""Generate job names for all tasks following the specified task"""
		job_names = []
		current_task_idx = list(self.task_to_internal_method_map).index(task)
		for idx, task in enumerate(self.task_to_internal_method_map.keys(), 0):
			if idx > current_task_idx:
				job_names.append(self.generate_job_name_for_task(task))
		return job_names

	def generate_job_name_for_all_tasks(self):
		"""Generate job names for all tasks in the deletion workflow"""
		job_names = []
		for task in self.task_to_internal_method_map.keys():
			job_names.append(self.generate_job_name_for_task(task))
		return job_names

	def before_submit(self):
		if queued_docs := frappe.db.get_all(
			"Transaction Deletion Record",
			filters={"status": ("in", ["Running", "Queued"]), "docstatus": 1},
			pluck="name",
		):
			frappe.throw(
				_(
					"Cannot start deletion. Another deletion {0} is already queued/running. Please wait for it to complete."
				).format(comma_and([get_link_to_form("Transaction Deletion Record", x) for x in queued_docs]))
			)

		if not self.doctypes_to_delete and not self.doctypes_to_be_ignored:
			frappe.throw(_("Please generate To Delete list before submitting"))

		if not self.doctypes_to_be_ignored:
			self.populate_doctypes_to_be_ignored_table()

	def reset_task_flags(self):
		self.clear_notifications_status = "Pending"
		self.delete_bin_data_status = "Pending"
		self.delete_leads_and_addresses_status = "Pending"
		self.delete_transactions_status = "Pending"
		self.initialize_doctypes_table_status = "Pending"
		self.reset_company_default_values_status = "Pending"

	def before_save(self):
		self.status = ""
		self.doctypes.clear()
		self.reset_task_flags()

	def on_submit(self):
		self.db_set("status", "Queued")
		self.start_deletion_tasks()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self._clear_deletion_cache()

	def _set_deletion_cache(self):
		"""Set Redis cache flags for per-doctype validation"""
		for item in self.doctypes_to_delete:
			frappe.cache.set_value(
				f"deletion_running_doctype:{item.doctype_name}",
				self.name,
				expires_in_sec=DELETION_CACHE_TTL,
			)

	def _clear_deletion_cache(self):
		"""Clear Redis cache flags"""
		for item in self.doctypes_to_delete:
			frappe.cache.delete_value(f"deletion_running_doctype:{item.doctype_name}")

	def _get_child_tables(self, doctype_name):
		"""Get list of child table DocType names for a given DocType

		Args:
		        doctype_name: The parent DocType to check

		Returns:
		        list: List of child table DocType names (Table field options)
		"""
		return frappe.get_all(
			"DocField", filters={"parent": doctype_name, "fieldtype": "Table"}, pluck="options"
		)

	def _get_to_delete_row_infos(self, doctype_name, company_field=None, company=None):
		"""Get child tables and document count for a To Delete list row

		Args:
		        doctype_name: The DocType to get information for
		        company_field: Optional company field name to filter by
		        company: Optional company value (defaults to self.company)

		Returns:
		        dict: {"child_doctypes": str, "document_count": int}
		"""
		company = company or self.company

		child_tables = self._get_child_tables(doctype_name)
		child_doctypes_str = ", ".join(child_tables) if child_tables else ""

		if company_field and company:
			doc_count = frappe.db.count(doctype_name, filters={company_field: company})
		else:
			doc_count = frappe.db.count(doctype_name)

		return {
			"child_doctypes": child_doctypes_str,
			"document_count": doc_count,
		}

	def _has_company_field(self, doctype_name):
		"""Check if DocType has a field specifically named 'company' linking to Company"""
		return frappe.db.exists(
			"DocField",
			{"parent": doctype_name, "fieldname": "company", "fieldtype": "Link", "options": "Company"},
		)

	def _get_company_link_fields(self, doctype_name):
		"""Get all Company Link field names for a DocType

		Args:
		        doctype_name: The DocType to check

		Returns:
		        list: List of field names that link to Company DocType, ordered by field index
		"""
		company_fields = frappe.get_all(
			"DocField",
			filters={"parent": doctype_name, "fieldtype": "Link", "options": "Company"},
			pluck="fieldname",
			order_by="idx",
		)
		return company_fields or []

	@frappe.whitelist()
	def generate_to_delete_list(self):
		"""Generate To Delete list with one row per company field"""
		self.doctypes_to_delete = []

		excluded = [d.doctype_name for d in self.doctypes_to_be_ignored]
		excluded.extend(_get_protected_doctypes_internal())
		excluded.append(self.doctype)  # Exclude self

		# Get all DocTypes that have Company link fields
		doctypes_with_company_field = frappe.get_all(
			"DocField",
			filters={"fieldtype": "Link", "options": "Company"},
			pluck="parent",
			distinct=True,
		)

		# Filter to get only valid DocTypes (not child tables, not virtual, not excluded)
		doctypes_with_company = []
		for doctype_name in doctypes_with_company_field:
			if doctype_name in excluded:
				continue

			# Check if doctype exists and is not a child table or virtual
			if frappe.db.exists("DocType", doctype_name):
				meta = frappe.get_meta(doctype_name)
				if not meta.istable and not meta.is_virtual:
					doctypes_with_company.append(doctype_name)

		for doctype_name in doctypes_with_company:
			# Get ALL company fields for this DocType
			company_fields = self._get_company_link_fields(doctype_name)

			# Get child tables once (same for all company fields of this DocType)
			child_tables = self._get_child_tables(doctype_name)
			child_doctypes_str = ", ".join(child_tables) if child_tables else ""

			for company_field in company_fields:
				doc_count = frappe.db.count(doctype_name, {company_field: self.company})

				self.append(
					"doctypes_to_delete",
					{
						"doctype_name": doctype_name,
						"company_field": company_field,
						"document_count": doc_count,
						"child_doctypes": child_doctypes_str,
					},
				)

		self.save()
		return {"count": len(self.doctypes_to_delete)}

	@frappe.whitelist()
	def populate_doctype_details(self, doctype_name, company=None, company_field=None):
		"""Get child DocTypes and document count for specified DocType

		Args:
		        doctype_name: The DocType to get details for
		        company: Optional company value for filtering (defaults to self.company)
		        company_field: Optional company field name to use for filtering
		"""
		frappe.only_for("System Manager")

		if not doctype_name:
			return {}

		if not frappe.db.exists("DocType", doctype_name):
			frappe.throw(_("DocType {0} does not exist").format(doctype_name))

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
			return self._get_to_delete_row_infos(doctype_name, company_field=company_field, company=company)
		except Exception as e:
			frappe.log_error(
				f"Error in populate_doctype_details for {doctype_name}: {e!s}", "Transaction Deletion Record"
			)
			return {
				"child_doctypes": "",
				"document_count": 0,
				"error": _("Unable to fetch DocType details. Please contact system administrator."),
			}

	def export_to_delete_template_method(self):
		"""Export To Delete list as CSV template"""
		if not self.doctypes_to_delete:
			frappe.throw(_("Generate To Delete list first"))

		import csv
		from io import StringIO

		output = StringIO()
		writer = csv.writer(output)
		writer.writerow(["doctype_name", "company_field", "child_doctypes"])

		for item in self.doctypes_to_delete:
			writer.writerow([item.doctype_name, item.company_field or "", item.child_doctypes or ""])

		frappe.response["result"] = output.getvalue()
		frappe.response["type"] = "csv"
		frappe.response[
			"doctype"
		] = f"deletion_template_{self.company}_{frappe.utils.now_datetime().strftime('%Y%m%d')}"

	def import_to_delete_template_method(self, csv_content):
		"""Import CSV template and regenerate counts"""
		import csv
		from io import StringIO

		reader = csv.DictReader(StringIO(csv_content))

		if "doctype_name" not in (reader.fieldnames or []):
			frappe.throw(_("Invalid CSV format. Expected column: doctype_name"))

		self.doctypes_to_delete = []
		protected = _get_protected_doctypes_internal()

		imported_count = 0
		skipped = []

		for row in reader:
			doctype_name = row.get("doctype_name", "").strip()
			company_field = row.get("company_field", "").strip() or None

			if not doctype_name:
				continue

			if doctype_name in protected:
				skipped.append(_("{0}: Protected DocType").format(doctype_name))
				continue

			if not frappe.db.exists("DocType", doctype_name):
				skipped.append(_("{0}: Not found").format(doctype_name))
				continue

			is_child = frappe.db.get_value("DocType", doctype_name, "istable")
			if is_child:
				skipped.append(_("{0}: Child table (auto-deleted with parent)").format(doctype_name))
				continue

			is_virtual = frappe.db.get_value("DocType", doctype_name, "is_virtual")
			if is_virtual:
				skipped.append(_("{0}: Virtual DocType (no database table)").format(doctype_name))
				continue

			db_company_fields = self._get_company_link_fields(doctype_name)
			import_company_field = ""
			if not db_company_fields:  # Case no company field exists
				details = self._get_to_delete_row_infos(doctype_name)
			elif (
				company_field and company_field in db_company_fields
			):  # Case it is provided by export and valid
				details = self._get_to_delete_row_infos(doctype_name, company_field)
				import_company_field = company_field
			else:  # Company field exists but not provided by export or invalid
				if "company" in db_company_fields:  # Check if 'company' is a valid field
					details = self._get_to_delete_row_infos(doctype_name, "company")
					import_company_field = "company"
				else:  # Fallback to first valid company field
					details = self._get_to_delete_row_infos(doctype_name, db_company_fields[0])
					import_company_field = db_company_fields[0]

			self.append(
				"doctypes_to_delete",
				{
					"doctype_name": doctype_name,
					"company_field": import_company_field,
					"document_count": details["document_count"],
					"child_doctypes": details["child_doctypes"],
				},
			)
			imported_count += 1

		self.save()

		if skipped:
			frappe.msgprint(
				_("Skipped {0} DocType(s):<br>{1}").format(len(skipped), "<br>".join(skipped)),
				title=_("Import Summary"),
				indicator="orange",
			)

		return {"imported": imported_count, "skipped": len(skipped)}

	def enqueue_task(self, task: str | None = None):
		"""Enqueue a deletion task for background execution"""
		if task and task in self.task_to_internal_method_map:
			job_names = self.generate_job_name_for_next_tasks(task=task)
			self.validate_running_task_for_doc(job_names=job_names)

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
					self._clear_deletion_cache()

	def delete_notifications(self):
		self.validate_doc_status()
		if self.clear_notifications_status == "Pending":
			clear_notifications()
			self.db_set("clear_notifications_status", "Completed")
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
		self._set_deletion_cache()
		self.enqueue_task(task="Delete Bins")

	def delete_bins(self):
		self.validate_doc_status()
		if self.delete_bin_data_status == "Pending":
			stock_related_doctypes = [
				"Item",
				"Warehouse",
				"Stock Entry",
				"Delivery Note",
				"Purchase Receipt",
				"Stock Reconciliation",
				"Material Request",
				"Purchase Invoice",
				"Sales Invoice",
			]

			if not self._is_any_doctype_in_deletion_list(stock_related_doctypes):
				self.db_set("delete_bin_data_status", "Skipped")
				self.enqueue_task(task="Delete Leads and Addresses")
				return

			frappe.db.sql(
				"""delete from `tabBin` where warehouse in
					(select name from tabWarehouse where company=%s)""",
				self.company,
			)
			self.db_set("delete_bin_data_status", "Completed")
		self.enqueue_task(task="Delete Leads and Addresses")

	def delete_lead_addresses(self):
		"""Delete addresses to which leads are linked"""
		self.validate_doc_status()
		if self.delete_leads_and_addresses_status == "Pending":
			if not self._is_any_doctype_in_deletion_list(["Lead"]):
				self.db_set("delete_leads_and_addresses_status", "Skipped")
				self.enqueue_task(task="Reset Company Values")
				return

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

			self.db_set("delete_leads_and_addresses_status", "Completed")
		self.enqueue_task(task="Reset Company Values")

	def reset_company_values(self):
		self.validate_doc_status()
		if self.reset_company_default_values_status == "Pending":
			sales_related_doctypes = [
				"Sales Order",
				"Sales Invoice",
				"Quotation",
				"Delivery Note",
			]

			if not self._is_any_doctype_in_deletion_list(sales_related_doctypes):
				self.db_set("reset_company_default_values_status", "Skipped")
				self.enqueue_task(task="Clear Notifications")
				return

			company_obj = frappe.get_doc("Company", self.company)
			company_obj.total_monthly_sales = 0
			company_obj.sales_monthly_history = None
			company_obj.save()
			self.db_set("reset_company_default_values_status", "Completed")
		self.enqueue_task(task="Clear Notifications")

	def initialize_doctypes_to_be_deleted_table(self):
		"""Initialize deletion table from To Delete list or fall back to original logic"""
		self.validate_doc_status()
		if self.initialize_doctypes_table_status == "Pending":
			# Use To Delete list if available (new behavior)
			if not self.doctypes_to_delete:
				frappe.throw(
					_("No DocTypes in To Delete list. Please generate or import the list before submitting."),
					title=_("Empty To Delete List"),
				)
			tables = self.get_all_child_doctypes()

			for to_delete_item in self.doctypes_to_delete:
				if to_delete_item.document_count > 0:
					# Add parent DocType only - child tables are handled automatically
					# by delete_child_tables() when the parent is deleted
					# Use company_field directly from To Delete item
					self.populate_doctypes_table(
						tables, to_delete_item.doctype_name, to_delete_item.company_field, 0
					)
			self.db_set("initialize_doctypes_table_status", "Completed")
		self.enqueue_task(task="Delete Transactions")

	def delete_company_transactions(self):
		self.validate_doc_status()
		if self.delete_transactions_status == "Pending":
			protected_doctypes = _get_protected_doctypes_internal()

			for docfield in self.doctypes:
				if docfield.doctype_name != self.doctype and not docfield.done:
					if docfield.doctype_name in protected_doctypes:
						error_msg = (
							f"CRITICAL: Attempted to delete protected DocType: {docfield.doctype_name}"
						)
						frappe.log_error(error_msg, "Transaction Deletion Security")
						frappe.throw(
							_("Cannot delete protected core DocType: {0}").format(docfield.doctype_name),
							title=_("Protected DocType"),
						)

					# Get company_field from stored value (could be any Company link field)
					company_field = docfield.docfield_name

					if company_field:
						no_of_docs = self.get_number_of_docs_linked_with_specified_company(
							docfield.doctype_name, company_field
						)
					else:
						no_of_docs = frappe.db.count(docfield.doctype_name)

					if no_of_docs > 0:
						if company_field:
							reference_docs = frappe.get_all(
								docfield.doctype_name,
								filters={company_field: self.company},
								fields=["name"],
								limit=self.batch_size,
							)
						else:
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
						naming_series = frappe.db.get_value("DocType", docfield.doctype_name, "autoname")
						if naming_series:
							if "#" in naming_series:
								self.update_naming_series(naming_series, docfield.doctype_name)
						frappe.db.set_value(docfield.doctype, docfield.name, "done", 1)

						to_delete_row = frappe.db.get_value(
							"Transaction Deletion Record To Delete",
							{
								"parent": self.name,
								"doctype_name": docfield.doctype_name,
								"company_field": company_field,
							},
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
				self.enqueue_task(task="Delete Transactions")
			else:
				self.db_set("status", "Completed")
				self.db_set("delete_transactions_status", "Completed")
				self.db_set("error_log", None)
				self._clear_deletion_cache()

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

	def populate_doctypes_table(self, tables, doctype, company_field, no_of_docs):
		"""Add doctype to processing tracker

		Args:
		        tables: List of child table DocType names (to exclude)
		        doctype: DocType name to track
		        company_field: Company link field name (or None)
		        no_of_docs: Initial count
		"""
		self.flags.ignore_validate_update_after_submit = True
		if doctype not in tables:
			self.append(
				"doctypes",
				{"doctype_name": doctype, "docfield_name": company_field, "no_of_docs": no_of_docs},
			)
		self.save(ignore_permissions=True)

	def delete_child_tables(self, doctype, reference_doc_names):
		child_tables = self._get_child_tables(doctype)

		for table in child_tables:
			frappe.db.delete(table, {"parent": ["in", reference_doc_names]})

	def delete_docs_linked_with_specified_company(self, doctype, reference_doc_names):
		frappe.db.delete(doctype, {"name": ("in", reference_doc_names)})

	@staticmethod
	def get_naming_series_prefix(naming_series: str, doctype_name: str) -> str:
		"""Extract the static prefix from an autoname pattern.

		Args:
		        naming_series: The autoname pattern (e.g., "PREFIX.####", "format:PRE-{####}")
		        doctype_name: DocType name for error logging

		Returns:
		        The static prefix before the counter placeholders
		"""
		if "." in naming_series:
			prefix = naming_series.rsplit(".", 1)[0]
		elif "{" in naming_series:
			prefix = naming_series.rsplit("{", 1)[0]
		else:
			# Fallback for unexpected patterns (shouldn't happen with valid Frappe naming series)
			frappe.log_error(
				title=_("Unexpected Naming Series Pattern"),
				message=_(
					"Naming series '{0}' for DocType '{1}' does not contain standard '.' or '{{' separator. Using fallback extraction."
				).format(naming_series, doctype_name),
			)
			prefix = naming_series.split("#", 1)[0] if "#" in naming_series else naming_series

		return prefix

	def update_naming_series(self, naming_series, doctype_name):
		# Derive a static prefix from the autoname pattern
		prefix = self.get_naming_series_prefix(naming_series, doctype_name)

		# Find the highest number used in the naming series to reset the counter
		doctype_table = qb.DocType(doctype_name)
		result = (
			qb.from_(doctype_table)
			.select(Max(doctype_table.name))
			.where(doctype_table.name.like(prefix + "%"))
			.run()
		)

		if result and result[0][0]:
			last = cint(result[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.set_value("Series", prefix, "current", last, update_modified=False)

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
	"""Export To Delete list as CSV via URL access"""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Transaction Deletion Record", name)
	doc.check_permission("read")
	return doc.export_to_delete_template_method()


@frappe.whitelist()
def process_import_template(transaction_deletion_record_name, file_url):
	"""Import CSV template and populate To Delete list"""
	import os

	doc = frappe.get_doc("Transaction Deletion Record", transaction_deletion_record_name)
	doc.check_permission("write")

	if not file_url or ".." in file_url:
		frappe.throw(_("Invalid file URL"))

	try:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
	except frappe.DoesNotExistError:
		frappe.throw(_("File not found"))

	if (
		file_doc.attached_to_doctype != "Transaction Deletion Record"
		or file_doc.attached_to_name != transaction_deletion_record_name
	):
		frappe.throw(_("File does not belong to this Transaction Deletion Record"))

	if not file_doc.file_name or not file_doc.file_name.lower().endswith(".csv"):
		frappe.throw(_("Only CSV files are allowed"))

	file_path = file_doc.get_full_path()

	if not os.path.isfile(file_path):
		frappe.throw(_("File not found on server"))

	with open(file_path, encoding="utf-8") as f:
		csv_content = f.read()

	return doc.import_to_delete_template_method(csv_content)


@frappe.whitelist()
@request_cache
def is_deletion_doc_running(company: str | None = None, err_msg: str | None = None):
	"""Check if any deletion is running globally

	The company parameter is kept for backwards compatibility but is now ignored.
	"""
	running_deletion_job = frappe.db.get_value(
		"Transaction Deletion Record",
		{"docstatus": 1, "status": ("in", ["Running", "Queued"])},
		"name",
	)

	if not running_deletion_job:
		return

	frappe.throw(
		title=_("Deletion in Progress!"),
		msg=_("Transaction Deletion Record {0} is already running. {1}").format(
			get_link_to_form("Transaction Deletion Record", running_deletion_job), err_msg or ""
		),
	)


def check_for_running_deletion_job(doc, method=None):
	"""Hook function called on document validate - checks Redis cache for running deletions"""
	if doc.doctype in LEDGER_ENTRY_DOCTYPES:
		return

	if doc.doctype in PROTECTED_CORE_DOCTYPES:
		return

	deletion_name = frappe.cache.get_value(f"deletion_running_doctype:{doc.doctype}")

	if deletion_name:
		frappe.throw(
			title=_("Deletion in Progress!"),
			msg=_(
				"Transaction Deletion Record {0} is currently deleting {1}. Cannot save documents until deletion completes."
			).format(
				get_link_to_form("Transaction Deletion Record", deletion_name), frappe.bold(doc.doctype)
			),
		)
