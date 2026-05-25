# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.background_jobs import is_job_enqueued


class PartyImport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.party_import_log.party_import_log import PartyImportLog

		create_customer_group: DF.Check
		create_supplier_group: DF.Check
		create_territory: DF.Check
		default_address_type: DF.Literal[
			"Billing",
			"Shipping",
			"Office",
			"Personal",
			"Plant",
			"Postal",
			"Shop",
			"Subsidiary",
			"Warehouse",
			"Current",
			"Permanent",
			"Other",
		]
		default_customer_group: DF.Link | None
		default_customer_type: DF.Literal["Company", "Individual", "Partnership"]
		default_supplier_group: DF.Link | None
		default_supplier_type: DF.Literal["Company", "Individual", "Partnership"]
		default_territory: DF.Link | None
		failed_count: DF.Int
		import_file: DF.Attach | None
		import_log: DF.Table[PartyImportLog]
		naming_series: DF.Literal["PIT-.YYYY.-"]
		party_type: DF.Literal["", "Customer", "Supplier"]
		skipped_count: DF.Int
		status: DF.Literal["Draft", "Pending", "Partial Success", "Success", "Error"]
		success_count: DF.Int
		total_records: DF.Int
	# end: auto-generated types

	def validate(self):
		doc_before_save = self.get_doc_before_save()
		file_changed = not self.import_file or (
			doc_before_save and doc_before_save.import_file != self.import_file
		)

		if file_changed:
			self.total_records = 0
			self.success_count = 0
			self.failed_count = 0
			self.skipped_count = 0
			self.import_log = []
			self.status = "Draft"

		self._validate_permissions()

		if self.import_file:
			self._validate_import_file()
			self._set_payload_count()

	def _validate_permissions(self):
		if not self.party_type:
			return
		if not frappe.has_permission(self.party_type, "import"):
			frappe.throw(
				_("You do not have import permission for {0}.").format(self.party_type),
				frappe.PermissionError,
			)

	def _validate_import_file(self):
		from erpnext.setup.doctype.party_import.party_importer import ImportFile

		try:
			ImportFile(self.import_file, self.party_type, validate_only=True)
		except frappe.ValidationError:
			raise
		except Exception as e:
			frappe.throw(_("Could not read import file: {0}").format(str(e)))

	def _set_payload_count(self):
		from erpnext.setup.doctype.party_import.party_importer import ImportFile

		try:
			imf = ImportFile(self.import_file, self.party_type, validate_only=True)
			self.total_records = imf.total_data_rows
		except Exception:
			pass

	@frappe.whitelist()
	def start_import(self):
		from frappe.utils.scheduler import is_scheduler_inactive

		if not self.import_file:
			frappe.throw(_("Please attach an import file first."))

		run_now = frappe.in_test or frappe.conf.developer_mode
		if is_scheduler_inactive() and not run_now:
			frappe.throw(_("Scheduler is inactive. Cannot import data."), title=_("Scheduler Inactive"))

		job_id = f"party_import||{self.name}"

		if is_job_enqueued(job_id):
			frappe.msgprint(_("Import is already running for this document."), indicator="orange", alert=True)
			return False

		self.db_set("status", "Pending", notify=True)
		frappe.db.commit()

		frappe.enqueue(
			"erpnext.setup.doctype.party_import.party_import.run_party_import",
			queue="default",
			timeout=10000,
			job_id=job_id,
			event="party_import",
			party_import=self.name,
			now=run_now,
		)

		return True

	def on_trash(self):
		frappe.db.delete("Party Import Log", {"parent": self.name})


def _check_permission(docname: str, ptype: str = "read"):
	if not frappe.has_permission("Party Import", doc=docname, ptype=ptype):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def run_party_import(party_import: str):
	from rq.timeouts import JobTimeoutException

	doc = frappe.get_doc("Party Import", party_import)

	frappe.flags.mute_emails = True

	try:
		from erpnext.setup.doctype.party_import.party_importer import PartyImporter

		PartyImporter(doc).run()

	except JobTimeoutException:
		frappe.db.rollback()
		doc.db_set("status", "Timed Out")
		frappe.log_error("Party Import timed out", "Party Import")

	except Exception:
		frappe.db.rollback()
		doc.db_set("status", "Error")
		frappe.log_error(frappe.get_traceback(), "Party Import Failed")

	finally:
		frappe.flags.mute_emails = False
		frappe.flags.in_import = False

	frappe.publish_realtime(
		"party_import_refresh",
		{"party_import": party_import},
		doctype="Party Import",
		docname=party_import,
	)


@frappe.whitelist()
def stop_import(party_import: str):
	from frappe.utils.background_jobs import get_redis_conn
	from rq.command import send_stop_job_command
	from rq.exceptions import InvalidJobOperation

	doc = frappe.get_doc("Party Import", party_import)
	doc.check_permission("write")

	job_id = f"{frappe.local.site}||party_import||{party_import}"

	try:
		send_stop_job_command(connection=get_redis_conn(), job_id=job_id)
		doc.db_set("status", "Error", notify=True)
		frappe.db.commit()
	except InvalidJobOperation:
		frappe.msgprint(_("Import job is not currently running."), indicator="orange", alert=True)

	return {"status": "stopped"}


@frappe.whitelist()
def get_template_fields(docname: str, party_type: str):
	_check_permission(docname)
	from erpnext.setup.doctype.party_import.party_importer import get_template_fields

	return get_template_fields(party_type)


@frappe.whitelist()
def get_party_count(docname: str, party_type: str):
	_check_permission(docname)
	doctype = "Supplier" if party_type == "Supplier" else "Customer"
	return frappe.db.count(doctype)


@frappe.whitelist()
def download_template(
	docname: str,
	party_type: str,
	fields: str | None = None,
	export_type: str = "blank_template",
	file_type: str = "xlsx",
):
	_check_permission(docname)

	import json

	from erpnext.setup.doctype.party_import.party_importer import get_template

	selected_fields = json.loads(fields) if fields else None
	file_type = (file_type or "xlsx").lower()
	if file_type not in ("xlsx", "csv"):
		file_type = "xlsx"

	data_rows = None
	if export_type in ("5_records", "all_records"):
		from erpnext.setup.doctype.party_import.party_importer import get_export_data

		limit = 5 if export_type == "5_records" else None
		data_rows = get_export_data(party_type, selected_fields, limit=limit)

	content, filename = get_template(party_type, selected_fields, data_rows=data_rows, file_type=file_type)

	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = "download"


@frappe.whitelist()
def export_errored_rows(docname: str):
	_check_permission(docname, ptype="read")

	doc = frappe.get_doc("Party Import", docname)

	if doc.status not in ("Partial Success", "Error"):
		frappe.throw(_("Errored rows can only be exported after a Partial Success or Error import."))

	if not doc.import_file:
		frappe.throw(_("No import file attached."))

	if not doc.import_log:
		frappe.throw(_("No import log found. Run the import first."))

	from erpnext.setup.doctype.party_import.party_importer import build_errored_rows_file

	content, filename = build_errored_rows_file(doc)

	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = "download"
