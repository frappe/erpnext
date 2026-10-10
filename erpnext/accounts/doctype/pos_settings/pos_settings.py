# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import Counter

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.model.document import Document

SEARCH_FIELD_TYPES = (
	"Data",
	"Link",
	"Dynamic Link",
	"Long Text",
	"Select",
	"Small Text",
	"Text",
	"Text Editor",
)

# Item fields that are of a searchable fieldtype, but are not meaningful to search a POS item by
DO_NOT_INCLUDE_FIELDS = (
	"naming_series",
	"item_code",
	"item_name",
	"stock_uom",
	"asset_naming_series",
	"default_material_request_type",
	"valuation_method",
	"warranty_period",
	"weight_uom",
	"batch_number_series",
	"serial_no_series",
	"purchase_uom",
	"customs_tariff_number",
	"sales_uom",
	"deferred_revenue_account",
	"deferred_expense_account",
	"quality_inspection_template",
	"route",
	"slideshow",
	"website_image_alt",
	"thumbnail",
	"web_long_description",
)


class POSSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pos_field.pos_field import POSField
		from erpnext.accounts.doctype.pos_search_fields.pos_search_fields import POSSearchFields

		invoice_fields: DF.Table[POSField]
		pos_search_fields: DF.Table[POSSearchFields]
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_invoice_fields()
		self.validate_invoice_fields()
		self.validate_duplicate_pos_search_fields()
		self.validate_pos_search_fields()

	def validate_duplicate_invoice_fields(self):
		fieldnames = [field.fieldname for field in self.invoice_fields]

		for fieldname, count in Counter(fieldnames).items():
			if count > 1:
				frappe.throw(
					title=_("Duplicate POS Fields"), msg=_("'{0}' has been already added.").format(fieldname)
				)

	def validate_invoice_fields(self):
		# the POS screen only ever creates a POS Invoice
		meta = frappe.get_meta("POS Invoice")

		for field in self.invoice_fields:
			df = meta.get_field(field.fieldname)

			if not df or not is_valid_invoice_field(df):
				frappe.throw(
					title=_("Invalid POS Field"),
					msg=_("Row #{0}: '{1}' is not a valid field of {2}.").format(
						field.idx, frappe.bold(field.fieldname or ""), frappe.bold(_("POS Invoice"))
					),
				)

			# read only in the form, so keep them in sync with the invoice
			field.label = df.label
			field.fieldtype = df.fieldtype
			field.options = df.options

	def validate_duplicate_pos_search_fields(self):
		fieldnames = [field.fieldname for field in self.pos_search_fields]

		for fieldname, count in Counter(fieldnames).items():
			if count > 1:
				frappe.throw(
					title=_("Duplicate POS Search Fields"),
					msg=_("'{0}' has been already added.").format(fieldname),
				)

	def validate_pos_search_fields(self):
		searchable_fields = {df.fieldname: df for df in get_searchable_item_fields()}

		for field in self.pos_search_fields:
			df = searchable_fields.get(field.fieldname)

			if not df:
				frappe.throw(
					title=_("Invalid POS Search Field"),
					msg=_("Row #{0}: '{1}' cannot be used to search items.").format(
						field.idx, frappe.bold(field.fieldname or "")
					),
				)

			if field.field != get_search_field_option(df):
				frappe.throw(
					title=_("Invalid POS Search Field"),
					msg=_("Row #{0}: '{1}' does not match {2}.").format(
						field.idx, frappe.bold(field.field or ""), frappe.bold(df.fieldname)
					),
				)


def is_valid_invoice_field(df):
	return df.fieldtype not in no_value_fields or df.fieldtype == "Button"


def get_searchable_item_fields():
	return [
		df
		for df in frappe.get_meta("Item").fields
		if df.fieldtype in SEARCH_FIELD_TYPES and df.fieldname not in DO_NOT_INCLUDE_FIELDS
	]


def get_search_field_option(df):
	# the fieldname keeps the option unique, two Item fields can share a label
	return f"{df.label} ({df.fieldname})"


@frappe.whitelist()
def get_pos_search_field_options():
	frappe.has_permission("POS Settings", throw=True)

	return [
		{"option": get_search_field_option(df), "fieldname": df.fieldname}
		for df in get_searchable_item_fields()
	]
