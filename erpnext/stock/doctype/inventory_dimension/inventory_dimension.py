# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _, bold, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document
from frappe.utils.caching import request_cache


class DoNotChangeError(frappe.ValidationError):
	pass


class CanNotBeChildDoc(frappe.ValidationError):
	pass


class CanNotBeDefaultDimension(frappe.ValidationError):
	pass


class InventoryDimensionNotEnabled(frappe.ValidationError):
	pass


def is_inventory_dimension_enabled() -> bool:
	"""Inventory Dimensions are gated behind a Stock Settings switch (Inventory Dimension tab).

	Tests set ``frappe.flags.enable_inventory_dimension`` so the feature can be toggled per-test
	without writing to (and leaking through) the committed Stock Settings single.
	"""
	if frappe.flags.get("enable_inventory_dimension") is not None:
		return bool(frappe.flags.enable_inventory_dimension)

	return bool(frappe.db.get_single_value("Stock Settings", "enable_inventory_dimension"))


@frappe.whitelist()
def inventory_dimension_enabled() -> bool:
	"""Whitelisted accessor for the client so the grids can toggle the dimension fields without
	requiring the user to have read permission on Stock Settings."""
	return is_inventory_dimension_enabled()


class InventoryDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		apply_to_all_doctypes: DF.Check
		condition: DF.Code | None
		dimension_name: DF.Data
		document_type: DF.Link | None
		fetch_from_parent: DF.Literal[None]
		istable: DF.Check
		negative_stock_validation_method: DF.Literal["Per Dimension", "Combined"]
		reference_document: DF.Link
		reqd: DF.Check
		source_fieldname: DF.Data | None
		target_fieldname: DF.Data | None
		type_of_transaction: DF.Literal["", "Inward", "Outward", "Both"]
		validate_negative_stock: DF.Check
	# end: auto-generated types

	ENTRY_DOCTYPE = "Inventory Dimension Entry"

	def onload(self):
		if not self.is_new() and frappe.db.has_column(self.ENTRY_DOCTYPE, self.source_fieldname):
			self.set_onload("has_stock_ledger", self.has_stock_ledger())

	def has_stock_ledger(self) -> str:
		if not self.source_fieldname or not frappe.db.has_column(self.ENTRY_DOCTYPE, self.source_fieldname):
			return

		# Dimension values now live on the quantity sub-ledger (Inventory Dimension Entry),
		# not on Stock Ledger Entry.
		return frappe.get_all(
			self.ENTRY_DOCTYPE,
			filters={self.source_fieldname: ("is", "set"), "is_cancelled": 0},
			limit=1,
		)

	def validate(self):
		self.validate_inventory_dimension_enabled()
		self.validate_reference_document()

	def validate_inventory_dimension_enabled(self):
		if not is_inventory_dimension_enabled():
			frappe.throw(
				_("Please enable {0} in {1} before creating an Inventory Dimension.").format(
					bold(_("Enable Inventory Dimension")), bold(_("Stock Settings"))
				),
				InventoryDimensionNotEnabled,
			)

	def before_save(self):
		self.do_not_update_document()
		self.reset_value()
		self.set_source_and_target_fieldname()
		self.set_type_of_transaction()

	def set_type_of_transaction(self):
		if self.apply_to_all_doctypes:
			self.type_of_transaction = "Both"

	def do_not_update_document(self):
		if self.is_new() or not self.has_stock_ledger():
			return

		old_doc = self._doc_before_save
		allow_to_edit_fields = [
			"fetch_from_parent",
			"type_of_transaction",
			"condition",
			"validate_negative_stock",
			"negative_stock_validation_method",
		]

		for field in frappe.get_meta("Inventory Dimension").fields:
			if field.fieldname not in allow_to_edit_fields and old_doc.get(field.fieldname) != self.get(
				field.fieldname
			):
				msg = f"""The user can not change value of the field {bold(field.label)} because
					stock transactions exists against the dimension {bold(self.name)}."""

				frappe.throw(_(msg), DoNotChangeError)

	def on_trash(self):
		self.delete_dimension_field()

	def delete_dimension_field(self):
		"""Remove the single dimension column from Inventory Dimension Entry."""
		name = frappe.db.get_value(
			"Custom Field", {"dt": self.ENTRY_DOCTYPE, "fieldname": self.source_fieldname}
		)
		if name:
			frappe.delete_doc("Custom Field", name)
			frappe.msgprint(
				_("Deleted the inventory dimension field {0}").format(bold(self.source_fieldname))
			)

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
			self.target_fieldname = scrub(self.dimension_name)

	def on_update(self):
		self.add_dimension_field()

	def add_dimension_field(self):
		"""Add a single Link column for this dimension to Inventory Dimension Entry.

		This replaces the previous behaviour of injecting custom fields into every stock
		transaction doctype (+ SLE + Stock Closing Balance). A new dimension now alters exactly
		one table - the quantity sub-ledger - instead of ~25, so large databases no longer take a
		storm of ``ALTER TABLE`` statements. Mandatory capture is enforced by the controller
		(``InventoryDimensionBundleService.validate_inventory_dimension_bundle``), gated on
		``is_stock_item``, rather than at field level.
		"""
		if frappe.db.get_value(
			"Custom Field", {"dt": self.ENTRY_DOCTYPE, "fieldname": self.source_fieldname}
		) or field_exists(self.ENTRY_DOCTYPE, self.source_fieldname):
			return

		create_custom_fields(
			{
				self.ENTRY_DOCTYPE: [
					dict(
						fieldname=self.source_fieldname,
						fieldtype="Link",
						insert_after="warehouse",
						options=self.reference_document,
						label=_(self.dimension_name),
						search_index=1,
						in_list_view=1,
					)
				]
			}
		)


def field_exists(doctype, fieldname) -> str | None:
	return frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, "name")


@frappe.whitelist()
def get_inventory_documents(
	doctype: Any | None = None,
	txt: str | None = None,
	searchfield: str | None = None,
	start: int | None = None,
	page_len: int | None = None,
	filters: dict | None = None,
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
		fields=["parent"],
		filters=and_filters,
		or_filters=or_filters,
		start=start,
		page_length=page_len,
		as_list=1,
		distinct=True,
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


@request_cache
def get_document_wise_inventory_dimensions(doctype) -> dict:
	return frappe.get_all(
		"Inventory Dimension",
		fields=[
			"name",
			"source_fieldname",
			"reference_document",
			"condition",
			"target_fieldname",
			"type_of_transaction",
			"fetch_from_parent",
			"reqd",
		],
		or_filters={"document_type": doctype, "apply_to_all_doctypes": 1},
	)


def get_voucher_child_doctype(voucher_type: str) -> str | None:
	"""The stock item child doctype for a voucher (e.g. Stock Entry -> Stock Entry Detail)."""
	if not voucher_type:
		return None

	meta = frappe.get_meta(voucher_type)
	field = meta.get_field("items")
	return field.options if field else None


def get_mandatory_inventory_dimensions(child_doctype: str) -> list:
	"""Mandatory (``reqd``) inventory dimensions applicable to a child doctype."""
	if not child_doctype:
		return []

	return [d for d in (get_document_wise_inventory_dimensions(child_doctype) or []) if d.get("reqd")]


@frappe.whitelist()
@request_cache
def get_inventory_dimensions():
	return frappe.get_all(
		"Inventory Dimension",
		fields=[
			"target_fieldname as fieldname",
			"source_fieldname",
			"reference_document as doctype",
			"validate_negative_stock",
			"negative_stock_validation_method",
			"name as dimension_name",
		],
		order_by="creation",  # pg-ok: dropped under distinct on PG — config-list iteration order only, not data
		distinct=True,
	)


@frappe.whitelist()
def delete_dimension(dimension: str):
	doc = frappe.get_doc("Inventory Dimension", dimension)
	doc.delete()


@frappe.whitelist()
def get_parent_fields(child_doctype: str, dimension_name: str):
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
