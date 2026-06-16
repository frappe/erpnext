# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import cint, get_link_to_form

NAME_PREFIX = "PB"


class ProductBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.selling.doctype.product_bundle_item.product_bundle_item import ProductBundleItem

		amended_from: DF.Link | None
		description: DF.Data | None
		disabled: DF.Check
		is_active: DF.Check
		items: DF.Table[ProductBundleItem]
		new_item_code: DF.Link
	# end: auto-generated types

	def autoname(self):
		"""BOM-style versioned name: ``PB-<parent item>-001``.

		Amended copies are excluded while computing the current index so that an
		amendment naturally becomes the next version of the bundle.
		"""
		search_key = f"{NAME_PREFIX}-{self.new_item_code}-%"
		existing = frappe.get_all(
			"Product Bundle",
			filters={"name": ("like", search_key), "amended_from": ["is", "not set"]},
			pluck="name",
		)
		index = get_next_version_index(existing)
		self.name = build_bundle_name(self.new_item_code, index)

	def validate(self):
		self.validate_main_item()
		self.validate_child_items()
		self.validate_child_items_qty_non_zero()
		from erpnext.utilities.transaction_base import validate_uom_is_integer

		validate_uom_is_integer(self, "uom", "qty")

	def on_submit(self):
		self.make_active()

	def on_cancel(self):
		self.db_set("is_active", 0)

	def on_update_after_submit(self):
		# `is_active` and `disabled` are the only fields editable after submit; keep a
		# single active version per parent item in sync when the user (re)activates a
		# version. `disabled` is orthogonal: it parks a version without ceding the
		# active slot, so re-enabling restores it without re-activation.
		if self.is_active:
			self.make_active()

	def make_active(self):
		"""Mark this version active and deactivate every other submitted version
		of the same parent item."""
		if not self.is_active:
			self.db_set("is_active", 1)

		others = frappe.get_all(
			"Product Bundle",
			filters={
				"new_item_code": self.new_item_code,
				"is_active": 1,
				"docstatus": 1,
				"name": ("!=", self.name),
			},
			pluck="name",
		)
		for name in others:
			frappe.db.set_value("Product Bundle", name, "is_active", 0)

	def on_trash(self):
		linked_doctypes = [
			"Delivery Note",
			"Sales Invoice",
			"POS Invoice",
			"Purchase Receipt",
			"Purchase Invoice",
			"Stock Entry",
			"Stock Reconciliation",
			"Sales Order",
			"Purchase Order",
			"Material Request",
		]

		invoice_links = []
		for doctype in linked_doctypes:
			item_doctype = doctype + " Item"

			if doctype == "Stock Entry":
				item_doctype = doctype + " Detail"

			invoices = frappe.db.get_all(
				item_doctype, {"item_code": self.new_item_code, "docstatus": 1}, ["parent"]
			)

			for invoice in invoices:
				invoice_links.append(get_link_to_form(doctype, invoice["parent"]))

		if len(invoice_links):
			frappe.throw(
				"This Product Bundle is linked with {}. You will have to cancel these documents in order to delete this Product Bundle".format(
					", ".join(invoice_links)
				),
				title=_("Not Allowed"),
			)

	def validate_main_item(self):
		"""Validates, main Item is not a stock item"""
		if frappe.db.get_value("Item", self.new_item_code, "is_stock_item"):
			frappe.throw(_("Parent Item {0} must not be a Stock Item").format(self.new_item_code))
		if frappe.db.get_value("Item", self.new_item_code, "is_fixed_asset"):
			frappe.throw(_("Parent Item {0} must not be a Fixed Asset").format(self.new_item_code))

	def validate_child_items(self):
		for item in self.items:
			if get_active_product_bundle(item.item_code):
				frappe.throw(
					_(
						"Row #{0}: Child Item should not be a Product Bundle. Please remove Item {1} and Save"
					).format(item.idx, frappe.bold(item.item_code))
				)

	def validate_child_items_qty_non_zero(self):
		for item in self.items:
			if item.qty <= 0:
				frappe.throw(
					_(
						"Row #{0}: Quantity cannot be a non-positive number. Please increase the quantity or remove the Item {1}"
					).format(item.idx, frappe.bold(item.item_code))
				)


def build_bundle_name(item_code: str, index: int) -> str:
	"""Build a ``PB-<item>-NNN`` name, truncating the item part to stay within 140 chars."""
	suffix = "%.3i" % index
	name = f"{NAME_PREFIX}-{item_code}-{suffix}"
	if len(name) <= 140:
		return name

	truncated_length = 140 - (len(NAME_PREFIX) + len(suffix) + 2)
	truncated_item = item_code[:truncated_length].rsplit(" ", 1)[0]
	return f"{NAME_PREFIX}-{truncated_item}-{suffix}"


def get_next_version_index(existing_names: list[str]) -> int:
	"""Highest trailing version index across ``existing_names`` plus one (1 if none)."""
	pattern = "|".join(re.escape(delim) for delim in ("/", "-"))
	parts = [re.split(pattern, name) for name in existing_names]
	valid = [p for p in parts if len(p) > 1 and p[-1]]
	if not valid:
		return 1
	return max(cint(p[-1]) for p in valid) + 1


def get_active_product_bundle(item_code: str) -> str | None:
	"""Return the name of the active, enabled, submitted Product Bundle for
	``item_code``, else None.

	This is the single resolution entry point for every consumer of bundles; it
	replaces the legacy ``exists("Product Bundle", {name/new_item_code, disabled: 0})``
	lookups that assumed one mutable bundle per item. A disabled bundle resolves to
	None even if it still holds the active slot for its parent item.
	"""
	if not item_code:
		return None
	return frappe.db.get_value(
		"Product Bundle",
		{"new_item_code": item_code, "is_active": 1, "docstatus": 1, "disabled": 0},
		"name",
	)


@frappe.whitelist()
def make_new_version(source_name: str, target_doc: str | None = None):
	"""Create a fresh draft bundle copied from an existing (typically submitted) one.

	The copy keeps the same parent item and component rows but gets a new version
	name on submit; it does not carry over docstatus or the active flag.
	"""
	from frappe.model.mapper import get_mapped_doc

	def post_process(source, target):
		target.is_active = 1
		target.disabled = 0

	return get_mapped_doc(
		"Product Bundle",
		source_name,
		{
			"Product Bundle": {
				"doctype": "Product Bundle",
				"field_map": {"new_item_code": "new_item_code"},
				"field_no_map": ["amended_from", "is_active", "disabled"],
			},
			"Product Bundle Item": {
				"doctype": "Product Bundle Item",
			},
		},
		target_doc,
		post_process,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_new_item_code(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	# Items that already have a bundle are intentionally *not* excluded: creating a
	# bundle for such an item produces a new version that supersedes the active one
	# on submit (same as the "Create New Version" action).
	if not searchfield or searchfield == "name":
		searchfield = frappe.get_meta("Item").get("search_fields")

	searchfield = searchfield.split(",")
	searchfield.append("name")

	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_name)
		.where((item.is_stock_item == 0) & (item.is_fixed_asset == 0))
		.limit(page_len)
		.offset(start)
	)

	if searchfield:
		query = query.where(Criterion.any([item[fieldname].like(f"%{txt}%") for fieldname in searchfield]))

	return query.run()
