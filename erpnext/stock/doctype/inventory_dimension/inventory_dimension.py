# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document


class DoNotChangeError(frappe.ValidationError):
	pass


class CanNotBeChildDoc(frappe.ValidationError):
	pass


class CanNotBeDefaultDimension(frappe.ValidationError):
	pass


class InventoryDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		apply_to_all_doctypes: DF.Check
		condition: DF.Code | None
		dimension_name: DF.Data
		disabled: DF.Check
		document_type: DF.Link | None
		fetch_from_parent: DF.Literal[None]
		istable: DF.Check
		mandatory_depends_on: DF.SmallText | None
		reference_document: DF.Link
		reqd: DF.Check
		source_fieldname: DF.Data | None
		target_fieldname: DF.Data | None
		type_of_transaction: DF.Literal["", "Inward", "Outward", "Both"]
		validate_negative_stock: DF.Check
	# end: auto-generated types

	def onload(self):
		if not self.is_new() and frappe.db.has_column("Stock Ledger Entry", self.target_fieldname):
			self.set_onload("has_stock_ledger", self.has_stock_ledger())

	def has_stock_ledger(self) -> str:
		if not self.target_fieldname:
			return

		return frappe.get_all(
			"Stock Ledger Entry", filters={self.target_fieldname: ("is", "set"), "is_cancelled": 0}, limit=1
		)

	def validate(self):
		self.validate_reference_document()

	def before_save(self):
		self.do_not_update_document()
		self.reset_value()
		self.set_source_and_target_fieldname()
		self.set_type_of_transaction()
		self.set_fetch_value_from()

	def set_type_of_transaction(self):
		if self.apply_to_all_doctypes:
			self.type_of_transaction = "Both"

	def set_fetch_value_from(self):
		if self.apply_to_all_doctypes:
			self.fetch_from_parent = self.reference_document

	def do_not_update_document(self):
		if self.is_new() or not self.has_stock_ledger():
			return

		old_doc = self._doc_before_save
		allow_to_edit_fields = [
			"disabled",
			"fetch_from_parent",
			"type_of_transaction",
			"condition",
			"validate_negative_stock",
		]

		for field in frappe.get_meta("Inventory Dimension").fields:
			if field.fieldname not in allow_to_edit_fields and old_doc.get(field.fieldname) != self.get(
				field.fieldname
			):
				msg = f"""The user can not change value of the field {bold(field.label)} because
					stock transactions exists against the dimension {bold(self.name)}."""

				frappe.throw(_(msg), DoNotChangeError)

	def on_trash(self):
		self.delete_custom_fields()

	def delete_custom_fields(self):
		filters = {
			"fieldname": (
				"in",
				[
					self.source_fieldname,
					f"to_{self.source_fieldname}",
					f"from_{self.source_fieldname}",
					f"rejected_{self.source_fieldname}",
				],
			)
		}

		if self.document_type:
			filters["dt"] = self.document_type

		for field in frappe.get_all("Custom Field", filters=filters):
			frappe.delete_doc("Custom Field", field.name)

		msg = f"Deleted custom fields related to the dimension {self.name}"
		frappe.msgprint(_(msg))

	def reset_value(self):
		if self.apply_to_all_doctypes:
			self.type_of_transaction = ""

			self.istable = 0
			for field in ["document_type", "condition"]:
				self.set(field, None)

	def validate_reference_document(self):
		if frappe.get_cached_value("DocType", self.reference_document, "istable") == 1:
			msg = f"The reference document {self.reference_document} can not be child table."
			frappe.throw(_(msg), CanNotBeChildDoc)

		if self.reference_document in ["Batch", "Serial No", "Warehouse", "Item"]:
			msg = f"The reference document {self.reference_document} can not be an Inventory Dimension."
			frappe.throw(_(msg), CanNotBeDefaultDimension)

	def set_source_and_target_fieldname(self) -> None:
		if not self.source_fieldname:
			self.source_fieldname = scrub(self.dimension_name)

		if not self.target_fieldname:
			self.target_fieldname = scrub(self.reference_document)

	def on_update(self):
		self.add_custom_fields()

	@staticmethod
	def get_insert_after_fieldname(doctype):
		return frappe.get_all(
			"DocField",
			fields=["fieldname"],
			filters={"parent": doctype},
			order_by="idx desc",
			limit=1,
		)[0].fieldname

	def get_dimension_fields(self, doctype=None):
		if not doctype:
			doctype = self.document_type

		label_start_with = ""
		if doctype in ["Purchase Invoice Item", "Purchase Receipt Item"]:
			label_start_with = "Target"
		elif doctype in ["Sales Invoice Item", "Delivery Note Item", "Stock Entry Detail"]:
			label_start_with = "Source"

		label = self.dimension_name
		if label_start_with:
			label = f"{label_start_with} {self.dimension_name}"

		dimension_fields = [
			dict(
				fieldname="inventory_dimension",
				fieldtype="Section Break",
				insert_after=self.get_insert_after_fieldname(doctype),
				label=_("Inventory Dimension"),
				collapsible=1,
			),
			dict(
				fieldname=self.source_fieldname,
				fieldtype="Link",
				insert_after="inventory_dimension",
				options=self.reference_document,
				label=_(label),
				search_index=1,
				reqd=self.reqd,
				mandatory_depends_on=self.mandatory_depends_on,
			),
		]

		if doctype in ["Purchase Invoice Item", "Purchase Receipt Item"]:
			dimension_fields.append(
				dict(
					fieldname="rejected_" + self.source_fieldname,
					fieldtype="Link",
					insert_after=self.source_fieldname,
					options=self.reference_document,
					label=_("Rejected " + self.dimension_name),
					search_index=1,
					reqd=self.reqd,
					mandatory_depends_on=self.mandatory_depends_on,
				)
			)

		return dimension_fields

	def add_custom_fields(self):
		custom_fields = {}

		dimension_fields = []
		if self.apply_to_all_doctypes:
			for doctype in get_inventory_documents():
				dimension_fields = self.get_dimension_fields(doctype[0])
				self.add_transfer_field(doctype[0], dimension_fields)
				custom_fields.setdefault(doctype[0], dimension_fields)
		else:
			dimension_fields = self.get_dimension_fields()

			self.add_transfer_field(self.document_type, dimension_fields)
			custom_fields.setdefault(self.document_type, dimension_fields)

		if (
			dimension_fields
			and not frappe.db.get_value(
				"Custom Field", {"dt": "Stock Ledger Entry", "fieldname": self.target_fieldname}
			)
			and not field_exists("Stock Ledger Entry", self.target_fieldname)
		):
			dimension_field = dimension_fields[1]
			dimension_field["mandatory_depends_on"] = ""
			dimension_field["reqd"] = 0
			dimension_field["fieldname"] = self.target_fieldname
			custom_fields["Stock Ledger Entry"] = dimension_field

		filter_custom_fields = {}
		ignore_doctypes = ["Serial and Batch Bundle", "Serial and Batch Entry", "Pick List Item"]

		if custom_fields:
			for doctype, fields in custom_fields.items():
				if doctype in ignore_doctypes:
					continue

				if isinstance(fields, dict):
					fields = [fields]

				for field in fields:
					if not field_exists(doctype, field["fieldname"]):
						filter_custom_fields.setdefault(doctype, []).append(field)

		create_custom_fields(filter_custom_fields)

	def add_transfer_field(self, doctype, dimension_fields):
		if doctype not in [
			"Stock Entry Detail",
			"Sales Invoice Item",
			"Delivery Note Item",
			"Purchase Invoice Item",
			"Purchase Receipt Item",
		]:
			return

		fieldname_start_with = "to"
		label_start_with = "Target"
		display_depends_on = ""

		if doctype in ["Purchase Invoice Item", "Purchase Receipt Item"]:
			fieldname_start_with = "from"
			label_start_with = "Source"
			display_depends_on = "eval:parent.is_internal_supplier == 1"
		elif doctype != "Stock Entry Detail":
			display_depends_on = "eval:parent.is_internal_customer == 1"
		elif doctype == "Stock Entry Detail":
			display_depends_on = "eval:parent.purpose != 'Material Issue'"

		fieldname = f"{fieldname_start_with}_{self.source_fieldname}"
		label = f"{label_start_with} {self.dimension_name}"

		if field_exists(doctype, fieldname):
			return

		dimension_fields.extend(
			[
				dict(
					fieldname="inventory_dimension_col_break",
					fieldtype="Column Break",
					insert_after=self.source_fieldname,
				),
				dict(
					fieldname=fieldname,
					fieldtype="Link",
					insert_after="inventory_dimension_col_break",
					options=self.reference_document,
					label=label,
					depends_on=display_depends_on,
				),
			]
		)


def field_exists(doctype, fieldname) -> str or None:
	return frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, "name")


@frappe.whitelist()
def get_inventory_documents(
	doctype=None, txt=None, searchfield=None, start=None, page_len=None, filters=None
):
	and_filters = [["DocField", "parent", "not in", ["Batch", "Serial No", "Item Price"]]]
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


def get_evaluated_inventory_dimension(doc, sl_dict, parent_doc=None):
	dimensions = get_document_wise_inventory_dimensions(doc.doctype)
	filter_dimensions = []
	for row in dimensions:
		if row.type_of_transaction and row.type_of_transaction != "Both":
			if (
				row.type_of_transaction == "Inward"
				if doc.docstatus == 1
				else row.type_of_transaction != "Inward"
			) and sl_dict.actual_qty < 0:
				continue
			elif (
				row.type_of_transaction == "Outward"
				if doc.docstatus == 1
				else row.type_of_transaction != "Outward"
			) and sl_dict.actual_qty > 0:
				continue

		evals = {"doc": doc}
		if parent_doc:
			evals["parent"] = parent_doc

		if row.condition and frappe.safe_eval(row.condition, evals):
			filter_dimensions.append(row)
		else:
			filter_dimensions.append(row)

	return filter_dimensions


def get_document_wise_inventory_dimensions(doctype) -> dict:
	if not hasattr(frappe.local, "document_wise_inventory_dimensions"):
		frappe.local.document_wise_inventory_dimensions = {}

	if not frappe.local.document_wise_inventory_dimensions.get(doctype):
		dimensions = frappe.get_all(
			"Inventory Dimension",
			fields=[
				"name",
				"source_fieldname",
				"condition",
				"target_fieldname",
				"type_of_transaction",
				"fetch_from_parent",
			],
			filters={"disabled": 0},
			or_filters={"document_type": doctype, "apply_to_all_doctypes": 1},
		)

		frappe.local.document_wise_inventory_dimensions[doctype] = dimensions

	return frappe.local.document_wise_inventory_dimensions[doctype]


@frappe.whitelist()
def get_inventory_dimensions():
	if not hasattr(frappe.local, "inventory_dimensions"):
		frappe.local.inventory_dimensions = {}

	if not frappe.local.inventory_dimensions:
		dimensions = frappe.get_all(
			"Inventory Dimension",
			fields=[
				"distinct target_fieldname as fieldname",
				"reference_document as doctype",
				"validate_negative_stock",
			],
			filters={"disabled": 0},
		)

		frappe.local.inventory_dimensions = dimensions

	return frappe.local.inventory_dimensions


@frappe.whitelist()
def delete_dimension(dimension):
	doc = frappe.get_doc("Inventory Dimension", dimension)
	doc.delete()


@frappe.whitelist()
def get_parent_fields(child_doctype, dimension_name):
	parent_doctypes = frappe.get_all("DocField", fields=["parent"], filters={"options": child_doctype})

	fields = []

	fields.extend(
		frappe.get_all(
			"DocField",
			fields=["fieldname as value", "label"],
			filters={"options": dimension_name, "parent": ("in", [d.parent for d in parent_doctypes])},
		)
	)

	fields.extend(
		frappe.get_all(
			"Custom Field",
			fields=["fieldname as value", "label"],
			filters={"options": dimension_name, "dt": ("in", [d.parent for d in parent_doctypes])},
		)
	)

	return fields
