from copy import copy

import frappe
from frappe import _
from frappe.core.doctype.data_import.importer import Importer, Row
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.scheduler import is_scheduler_inactive
from rq.timeouts import JobTimeoutException

from erpnext.stock.serial_batch_fields import NUMBER_INPUT_DOCTYPES
from erpnext.stock.serial_batch_input import NUMBER_FIELDS


class SerialBatchDataImport:
	def get_importer(self):
		if not has_number_inputs(self.reference_doctype):
			return super().get_importer()
		return SerialBatchImporter(self.reference_doctype, data_import=self, use_sniffer=self.use_csv_sniffer)

	def start_import(self):
		if not has_number_inputs(self.reference_doctype):
			return super().start_import()
		run_now = frappe.in_test or frappe.conf.developer_mode
		if is_scheduler_inactive() and not run_now:
			frappe.throw(_("Scheduler is inactive. Cannot import data."), title=_("Scheduler Inactive"))
		job_id = f"data_import||{self.name}"
		if not is_job_enqueued(job_id):
			frappe.enqueue(
				start_import,
				queue="default",
				timeout=10000,
				event="data_import",
				job_id=job_id,
				data_import=self.name,
				now=run_now,
				enqueue_after_commit=True,
			)
			return True


def start_import(data_import):
	data_import = frappe.get_doc("Data Import", data_import)
	data_import.set_delimiters_flag()
	try:
		data_import.get_importer().import_data()
	except JobTimeoutException:
		frappe.db.rollback()
		data_import.db_set("status", "Timed Out")
	except Exception:
		frappe.db.rollback()
		data_import.db_set("status", "Error")
		data_import.log_error("Data import failed")
	finally:
		frappe.flags.in_import = False
	frappe.publish_realtime(
		"data_import_refresh", {"data_import": data_import.name}, user=frappe.session.user
	)


class SerialBatchImporter(Importer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.template_options.get("serial_batch_input") is False:
			return
		for column in self.import_file.header.columns:
			df = column.df
			if column.skip_import or not df or df.parent not in NUMBER_INPUT_DOCTYPES:
				continue
			if df.fieldname == "batch_no":
				# Import cells contain physical numbers; validate their links after item resolution.
				column.df = copy(df)
				column.df.fieldtype = "Data"
				column.warnings = [warning for warning in column.warnings if warning.get("type") == "info"]
				column.invalid_value_items = None
		self.import_file.data = [
			SerialBatchImportRow(row.index, row.data, row.doctype, row.header, row.import_type)
			for row in self.import_file.data
		]


class SerialBatchImportRow(Row):
	def _parse_doc(self, doctype, columns, values, parent_doc=None, table_df=None):
		doc = super()._parse_doc(doctype, columns, values, parent_doc, table_df)
		if doctype in NUMBER_INPUT_DOCTYPES:
			fields = [
				column.df.fieldname
				for column, value in zip(columns, values, strict=True)
				if column.df.fieldname in NUMBER_FIELDS and value not in (None, "")
			]
			if fields:
				doc.update({"__serial_batch_input": fields})
		return doc


def has_number_inputs(doctype):
	return any(df.options in NUMBER_INPUT_DOCTYPES for df in frappe.get_meta(doctype).get_table_fields())
