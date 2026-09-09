from copy import copy

import frappe
from frappe.core.doctype.data_import.importer import Importer, Row

from erpnext.stock.serial_batch_input import NUMBER_FIELDS


class SerialBatchDataImport:
	def get_importer(self):
		if not has_number_inputs(self.reference_doctype):
			return super().get_importer()
		return SerialBatchImporter(self.reference_doctype, data_import=self, use_sniffer=self.use_csv_sniffer)


class SerialBatchImporter(Importer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.template_options.get("serial_batch_input") is False:
			return
		for column in self.import_file.header.columns:
			df = column.df
			if (
				column.skip_import
				or not df
				or not frappe.get_meta(df.parent).has_field("serial_and_batch_bundle")
			):
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
		if frappe.get_meta(doctype).has_field("serial_and_batch_bundle"):
			fields = [
				column.df.fieldname
				for column, value in zip(columns, values, strict=True)
				if column.df.fieldname in NUMBER_FIELDS and value not in (None, "")
			]
			if fields:
				doc.update({"__serial_batch_input": fields})
		return doc


def has_number_inputs(doctype):
	return any(
		frappe.get_meta(df.options).has_field("serial_and_batch_bundle")
		for df in frappe.get_meta(doctype).get_table_fields()
	)
