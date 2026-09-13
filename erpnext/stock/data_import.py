import frappe
from frappe import _
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.core.doctype.data_import.importer import INVALID_VALUES, Importer, Row, df_as_json
from frappe.model.utils.user_settings import get_user_settings
from frappe.utils import cstr, escape_html

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


class ERPNextDataImport:
	def get_importer(self):
		return ERPNextImporter(self.reference_doctype, data_import=self, use_sniffer=self.use_csv_sniffer)


class ERPNextImporter(Importer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.serial_batch_columns = {
			col.index
			for col in self.import_file.columns
			if not col.skip_import and is_serial_batch_link(col.df, self.doctype)
		}
		if not self.serial_batch_columns:
			return

		for index in self.serial_batch_columns:
			col = self.import_file.columns[index]
			col.invalid_value_items = []
			col.warnings = [warning for warning in col.warnings if warning.get("type") != "value_mapping"]
		record_ids = {}
		self.import_file.data = [
			SerialBatchImportRow(row, self.serial_batch_columns, record_ids) for row in self.import_file.data
		]

	def get_data_for_import_preview(self):
		if self.serial_batch_columns:
			self.import_file.get_payloads_for_import()
		return super().get_data_for_import_preview()


class SerialBatchImportRow(Row):
	def __init__(self, row, serial_batch_columns, record_ids):
		super().__init__(row.index, row.data, row.doctype, row.header, row.import_type)
		self.serial_batch_columns = serial_batch_columns
		self.record_ids = record_ids

	def _parse_doc(self, doctype, columns, values, parent_doc=None, table_df=None):
		doc = super()._parse_doc(
			doctype,
			columns,
			[
				None if col.index in self.serial_batch_columns else value
				for col, value in zip(columns, values, strict=True)
			],
			parent_doc,
			table_df,
		)
		item_field = get_item_field(doctype)
		item_code = doc.get(item_field) or (parent_doc or {}).get(get_item_field(self.doctype))
		for col, value in zip(columns, values, strict=True):
			if col.index not in self.serial_batch_columns or value in INVALID_VALUES:
				continue
			if record_id := self.resolve_number(col, item_code, cstr(value).strip()):
				doc.update({col.df.fieldname: record_id})
		return doc

	def resolve_number(self, col, item_code, number):
		doctype = col.df.options
		if not item_code:
			message = _("Include the Item Code to import {0} {1}.").format(_(doctype), escape_html(number))
		else:
			key = (doctype, item_code, number)
			if key not in self.record_ids:
				self.record_ids[key] = SerialBatchIdentity(doctype).get_records(
					item_code, [number], ["name"], ignore_permissions=False
				)
			records = self.record_ids[key]
			if len(records) == 1:
				return records[0].name
			message = _("Could not select {0} {1} for Item {2}.").format(
				_(doctype), escape_html(number), escape_html(item_code)
			)
		warning = {"row": self.row_number, "field": df_as_json(col.df), "message": message}
		if warning not in self.warnings:
			self.warnings.append(warning)


class ERPNextExporter(Exporter):
	def get_all_exportable_fields(self):
		fields = super().get_all_exportable_fields()
		item_columns = {}
		for key, columns in fields.items():
			for df in columns:
				if not is_serial_batch_link(df, self.doctype):
					continue
				if item_field := get_item_field(df.parent):
					item_columns[key] = (df.parent, item_field)
				if item_field := get_item_field(self.doctype):
					item_columns[self.doctype] = (self.doctype, item_field)
		for key, (doctype, item_field) in item_columns.items():
			columns = fields.setdefault(key, [])
			if any(column.fieldname == item_field for column in columns):
				continue
			permitted = self.get_exportable_fields(doctype, [item_field])
			if not permitted:
				frappe.throw(
					_("Item Code access is required to export physical serial and batch numbers."),
					frappe.PermissionError,
				)
			columns.extend(permitted)
		return fields

	def get_data_as_docs(self):
		for doc in super().get_data_as_docs():
			number_cells = {"Serial No": [], "Batch": []}
			for key, fields in self.exportable_fields.items():
				rows = [doc] if key == self.doctype else doc.get(key, [])
				for df in fields:
					if is_serial_batch_link(df, self.doctype):
						number_cells[df.options].extend(
							(row, df.fieldname, row[df.fieldname]) for row in rows if row.get(df.fieldname)
						)
			for doctype, cells in number_cells.items():
				if not cells:
					continue
				numbers = dict(
					frappe.get_all(
						doctype,
						filters={"name": ("in", list({name for row, field, name in cells}))},
						fields=["name", SerialBatchIdentity(doctype).number_field],
						as_list=True,
					)
				)
				for row, field, name in cells:
					if name not in numbers:
						frappe.throw(
							_("A linked {0} no longer exists. Correct the document before exporting.").format(
								_(doctype)
							)
						)
					row[field] = numbers[name]
			yield doc


@frappe.whitelist()
def download_template(
	doctype: str,
	export_fields: str | dict | None = None,
	export_records: str | None = None,
	export_filters: str | dict | list | None = None,
	file_type: str = "CSV",
):
	frappe.has_permission(doctype, "read", throw=True)
	list_settings = frappe.parse_json(get_user_settings(doctype)).get("List", {})
	sort_by = list_settings.get("sort_by")
	sort_order = list_settings.get("sort_order")
	order_by = None
	if (
		sort_by
		and frappe.get_meta(doctype).get_field(sort_by)
		and sort_order
		and sort_order.upper() in ("ASC", "DESC")
	):
		order_by = f"{sort_by} {sort_order}"
	ERPNextExporter(
		doctype,
		export_fields=frappe.parse_json(export_fields),
		export_data=export_records != "blank_template",
		export_filters=frappe.parse_json(export_filters),
		file_type=file_type,
		export_page_length=5 if export_records == "5_records" else None,
		order_by=order_by,
	).build_response()


def is_serial_batch_link(df, parent_doctype):
	return (
		df
		and df.fieldtype == "Link"
		and df.options in ("Serial No", "Batch")
		and (get_item_field(df.parent) or get_item_field(parent_doctype))
	)


def get_item_field(doctype):
	meta = frappe.get_meta(doctype)
	return next(
		(
			fieldname
			for fieldname in ("item_code", "rm_item_code", "item")
			if (df := meta.get_field(fieldname)) and df.fieldtype == "Link" and df.options == "Item"
		),
		None,
	)
