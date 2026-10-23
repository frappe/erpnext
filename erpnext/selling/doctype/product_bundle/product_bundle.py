# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import get_link_to_form


class ProductBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.selling.doctype.product_bundle_item.product_bundle_item import ProductBundleItem

		description: DF.Data | None
		disabled: DF.Check
		items: DF.Table[ProductBundleItem]
		new_item_code: DF.Link
	# end: auto-generated types

	def autoname(self):
		self.name = self.new_item_code

	def validate(self):
		self.validate_main_item()
		self.validate_child_items()
		if not self.disabled:
			# a disabled bundle is being retired and is never packed, so don't let these
			# integrity checks block saving (e.g. disabling) a pre-existing bad bundle
			self.validate_not_nested()
			self.validate_duplicate_items()
			self.validate_child_items_uom()
		self.validate_child_items_qty_non_zero()
		from erpnext.utilities.transaction_base import validate_uom_is_integer

		validate_uom_is_integer(self, "uom", "qty")

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
			if item.item_code == self.new_item_code:
				frappe.throw(
					_("Row #{0}: A Product Bundle cannot contain its own parent Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					)
				)
			if frappe.db.exists("Product Bundle", {"name": item.item_code, "disabled": 0}):
				frappe.throw(
					_(
						"Row #{0}: Child Item should not be a Product Bundle. Please remove Item {1} and Save"
					).format(item.idx, frappe.bold(item.item_code))
				)

	def validate_not_nested(self):
		# the parent item must not already be a component of another enabled bundle,
		# otherwise that bundle would silently nest this one
		pb = frappe.qb.DocType("Product Bundle")
		pbi = frappe.qb.DocType("Product Bundle Item")
		outer = (
			frappe.qb.from_(pbi)
			.join(pb)
			.on(pbi.parent == pb.name)
			.select(pb.name)
			.where((pbi.item_code == self.new_item_code) & (pb.name != self.name) & (pb.disabled == 0))
			.limit(1)
		).run(pluck=True)
		if outer:
			frappe.throw(
				_(
					"Item {0} is already a component of Product Bundle {1}; nested bundles are not supported."
				).format(frappe.bold(self.new_item_code), frappe.bold(outer[0])),
				title=_("Nested Product Bundle"),
			)

	def validate_child_items_uom(self):
		# a component's UOM must resolve the same way packing's get_conversion_factor does:
		# the item or its template's UOM Conversion Detail, else a global UOM Conversion Factor
		from erpnext.stock.doctype.item.item import get_uom_conv_factor

		for item in self.items:
			if not item.uom:
				continue
			item_info = frappe.db.get_value("Item", item.item_code, ["stock_uom", "variant_of"], as_dict=True)
			if not item_info or item.uom == item_info.stock_uom:
				continue
			stock_uom, variant_of = item_info.stock_uom, item_info.variant_of
			parents = [item.item_code, variant_of] if variant_of else [item.item_code]
			if frappe.db.exists("UOM Conversion Detail", {"parent": ["in", parents], "uom": item.uom}):
				continue
			if get_uom_conv_factor(item.uom, stock_uom):
				continue
			frappe.throw(
				_(
					"Row #{0}: UOM {1} is not configured for Item {2}. Add a UOM conversion on the Item or use its stock UOM."
				).format(item.idx, frappe.bold(item.uom), frappe.bold(item.item_code))
			)

	def validate_duplicate_items(self):
		# a component repeated across rows breaks the packed-item keying downstream
		seen = set()
		for item in self.items:
			if item.item_code in seen:
				frappe.throw(
					_(
						"Row #{0}: Item {1} is already added. Combine the quantities into a single row."
					).format(item.idx, frappe.bold(item.item_code))
				)
			seen.add(item.item_code)

	def validate_child_items_qty_non_zero(self):
		for item in self.items:
			if item.qty <= 0:
				frappe.throw(
					_(
						"Row #{0}: Quantity cannot be a non-positive number. Please increase the quantity or remove the Item {1}"
					).format(item.idx, frappe.bold(item.item_code))
				)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_new_item_code(doctype, txt, searchfield, start, page_len, filters):
	product_bundles = frappe.db.get_list("Product Bundle", {"disabled": 0}, pluck="name")

	if not searchfield or searchfield == "name":
		searchfield = frappe.get_meta("Item").get("search_fields")

	searchfield = searchfield.split(",")
	searchfield.append("name")

	item_filters = [["is_stock_item", "=", 0], ["is_fixed_asset", "=", 0]]
	if product_bundles:
		item_filters.append(["name", "not in", product_bundles])

	# get_list applies Item's permission conditions and User Permissions, as item_query() does
	return frappe.get_list(
		"Item",
		filters=item_filters,
		or_filters=[[fieldname, "like", f"%{txt}%"] for fieldname in searchfield] if searchfield else None,
		fields=["name", "item_name"],
		order_by="",  # the query this replaced had no ORDER BY; suppress the injected default
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)
