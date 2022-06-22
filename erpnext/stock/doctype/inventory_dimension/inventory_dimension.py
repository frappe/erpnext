# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document


class InventoryDimension(Document):
	def validate(self):
		self.reset_value()
		self.validate_reference_document()
		self.set_source_and_target_fieldname()

	def reset_value(self):
		if self.apply_to_all_doctypes:
			self.istable = 0
			for field in ["document_type", "parent_field", "condition", "type_of_transaction"]:
				self.set(field, None)

	def validate_reference_document(self):
		if frappe.get_cached_value("DocType", self.reference_document, "istable") == 1:
			frappe.throw(_(f"The reference document {self.reference_document} can not be child table."))

		if self.reference_document in ["Batch", "Serial No", "Warehouse", "Item"]:
			frappe.throw(
				_(f"The reference document {self.reference_document} can not be an Inventory Dimension.")
			)

	def set_source_and_target_fieldname(self):
		self.source_fieldname = scrub(self.dimension_name)
		if not self.map_with_existing_field:
			self.target_fieldname = self.source_fieldname

	def on_update(self):
		self.add_custom_fields()

	def add_custom_fields(self):
		dimension_field = dict(
			fieldname=self.source_fieldname,
			fieldtype="Link",
			insert_after="warehouse",
			options=self.reference_document,
			label=self.dimension_name,
		)

		custom_fields = {}

		if self.apply_to_all_doctypes:
			for doctype in get_inventory_documents():
				if not frappe.db.get_value(
					"Custom Field", {"dt": doctype[0], "fieldname": self.source_fieldname}
				):
					custom_fields.setdefault(doctype[0], dimension_field)
		elif not frappe.db.get_value(
			"Custom Field", {"dt": self.document_type, "fieldname": self.source_fieldname}
		):
			custom_fields.setdefault(self.document_type, dimension_field)

		if not frappe.db.get_value(
			"Custom Field", {"dt": "Stock Ledger Entry", "fieldname": self.target_fieldname}
		):
			dimension_field["fieldname"] = self.target_fieldname
			custom_fields["Stock Ledger Entry"] = dimension_field

		create_custom_fields(custom_fields)


@frappe.whitelist()
def get_inventory_documents(
	doctype=None, txt=None, searchfield=None, start=None, page_len=None, filters=None
):
	and_filters = [["DocField", "parent", "not in", ["Batch", "Serial No"]]]
	or_filters = [
		["DocField", "options", "in", ["Batch", "Serial No"]],
		["DocField", "parent", "in", ["Putaway Rule"]],
	]

	if txt:
		and_filters.append(["DocField", "parent", "like", f"%{txt}%"])

	return frappe.get_all(
		"DocField",
		fields=["distinct parent"],
		filters=and_filters,
		or_filters=or_filters,
		start=start,
		page_length=page_len,
		as_list=1,
	)


def get_evaluated_inventory_dimension(doc, sl_dict, parent_doc=None) -> dict:
	dimensions = get_document_wise_inventory_dimensions(doc.doctype)
	for row in dimensions:
		if (
			row.type_of_transaction == "Inward"
			if doc.docstatus == 1
			else row.type_of_transaction != "Inward"
		) and sl_dict.actual_qty < 0:
			continue
		elif (
			row.type_of_transaction == "Outward"
			if doc.docstatus == 1
			else row.type_of_transaction != "Inward"
		) and sl_dict.actual_qty > 0:
			continue

		if frappe.safe_eval(row.condition, {"doc": doc, "parent_doc": parent_doc}):
			return row


def get_document_wise_inventory_dimensions(doctype) -> dict:
	if not hasattr(frappe.local, "document_wise_inventory_dimensions"):
		frappe.local.document_wise_inventory_dimensions = {}

	if doctype not in frappe.local.document_wise_inventory_dimensions:
		dimensions = frappe.get_all(
			"Inventory Dimension",
			fields=["name", "source_fieldname", "condition", "target_fieldname", "type_of_transaction"],
			filters={"disabled": 0},
			or_filters={"document_type": doctype, "apply_to_all_doctypes": 1},
		)

		frappe.local.document_wise_inventory_dimensions[doctype] = dimensions

	return frappe.local.document_wise_inventory_dimensions[doctype]


@frappe.whitelist()
def get_source_fieldnames(reference_document, ignore_document):
	return frappe.get_all(
		"Inventory Dimension",
		fields=["source_fieldname as value", "dimension_name as label"],
		filters={
			"disabled": 0,
			"map_with_existing_field": 0,
			"name": ("!=", ignore_document),
			"reference_document": reference_document,
		},
	)


@frappe.whitelist()
def get_inventory_dimensions():
	if not hasattr(frappe.local, "inventory_dimensions"):
		frappe.local.inventory_dimensions = {}

	if not frappe.local.inventory_dimensions:
		dimensions = frappe.get_all(
			"Inventory Dimension",
			fields=[
				"distinct target_fieldname as fieldname",
				"dimension_name as label",
				"reference_document as doctype",
			],
			filters={"disabled": 0, "map_with_existing_field": 0},
		)

		frappe.local.inventory_dimensions = dimensions

	return frappe.local.inventory_dimensions
