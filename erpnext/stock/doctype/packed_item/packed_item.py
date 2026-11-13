# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt


import json
from collections import Counter

import frappe
import frappe.defaults
from frappe.model.document import Document
from frappe.utils import cint, flt

from erpnext.stock.get_item_details import get_conversion_factor, get_item_details, get_price_list_rate


class PackedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_batch_qty: DF.Float
		actual_qty: DF.Float
		batch_no: DF.Link | None
		conversion_factor: DF.Float
		delivered_by_supplier: DF.Check
		description: DF.TextEditor | None
		incoming_rate: DF.Currency
		item_code: DF.Link | None
		item_name: DF.Data | None
		ordered_qty: DF.Float
		packed_qty: DF.Float
		page_break: DF.Check
		parent: DF.Data
		parent_detail_docname: DF.Data | None
		parent_item: DF.Link | None
		parentfield: DF.Data
		parenttype: DF.Data
		picked_qty: DF.Float
		prevdoc_doctype: DF.Data | None
		projected_qty: DF.Float
		qty: DF.Float
		rate: DF.Currency
		received_qty: DF.Float
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		target_warehouse: DF.Link | None
		uom: DF.Link | None
		use_serial_batch_fields: DF.Check
		warehouse: DF.Link | None
	# end: auto-generated types

	pass


def make_packing_list(doc):
	"Make/Update packing list for Product Bundle Item."
	if doc.get("_action") and doc._action == "update_after_submit":
		return

	parent_items_price, reset = {}, False
	set_price_from_children = frappe.db.get_single_value("Selling Settings", "editable_bundle_item_rates")

	stale_packed_items_table = get_indexed_packed_items_table(doc)
	order_packed_items = get_order_packed_items(doc)

	reset = reset_packing_list(doc)

	for item_row in doc.get("items"):
<<<<<<< HEAD
		if is_product_bundle(item_row.item_code):
			so_packed_items = list(order_packed_items.get(get_order_row(doc, item_row), []))
			for bundle_item in get_product_bundle_items(item_row.item_code):
				pi_row = add_packed_item_row(
					doc=doc,
					packing_item=bundle_item,
					main_item_row=item_row,
					packed_items_table=stale_packed_items_table,
					reset=reset,
				)
				item_data = get_packed_item_details(bundle_item.item_code, doc.company)
				so_packed_item = pop_order_packed_item(
					so_packed_items, item_row.item_code, bundle_item.item_code
				)
				update_packed_item_basic_data(item_row, pi_row, bundle_item, item_data, so_packed_item)
				update_packed_item_stock_data(item_row, pi_row, bundle_item, item_data, doc)
				update_packed_item_price_data(pi_row, item_data, doc)
=======
		# Pack from the version chosen on the row (default: the item's active version)
		# and record it so the document keeps a reference to the exact version used.
		bundle_name = get_bundle_version_for_row(item_row, doc)
		if item_row.meta.has_field("product_bundle"):
			item_row.product_bundle = bundle_name
		if item_row.meta.has_field("is_product_bundle"):
			item_row.is_product_bundle = 1 if bundle_name else 0

		if bundle_name:
			for bundle_item, so_packed_item in get_bundle_components(
				doc, item_row, bundle_name, order_packed_items
			):
				item_data = get_packed_item_details(bundle_item.item_code, doc.company)
				# a component picked from several locations gets a packed row per location
				locations = get_pick_list_locations(
					doc, item_row, bundle_item, item_data, so_packed_item, stale_packed_items_table
				)
				for location in locations or [None]:
					pi_row = add_packed_item_row(
						doc=doc,
						packing_item=bundle_item,
						main_item_row=item_row,
						packed_items_table=stale_packed_items_table,
						reset=reset,
						sales_order_packed_item=get_sales_order_packed_item(doc, so_packed_item),
						location=location,
					)
					pi_row.product_bundle = bundle_name
					update_packed_item_basic_data(item_row, pi_row, bundle_item, item_data, so_packed_item)
					update_packed_item_stock_data(
						item_row, pi_row, bundle_item, item_data, doc, so_packed_item
					)
					update_packed_item_price_data(pi_row, item_data, doc)
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)

					if location:
						update_packed_item_with_pick_list_info(item_row, pi_row, location)

<<<<<<< HEAD
				update_packed_item_from_cancelled_doc(item_row, bundle_item, pi_row, doc)

				if set_price_from_children:  # create/update bundle item wise price dict
					update_product_bundle_rate(parent_items_price, pi_row, item_row)
=======
					if set_price_from_children:  # create/update bundle item wise price dict
						update_product_bundle_rate(parent_items_price, pi_row, item_row)

	if not reset:
		remove_unused_pick_list_rows(doc, stale_packed_items_table)
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)

	if parent_items_price:
		set_product_bundle_rate_amount(doc, parent_items_price)  # set price in bundle item


<<<<<<< HEAD
=======
def get_bundle_components(doc, item_row, bundle_name, order_packed_items):
	"""Components of ``item_row``'s bundle, each with the order's packed row it delivers."""
	order_row = item_row.name if doc.doctype == "Sales Order" else get_order_row(doc, item_row)
	so_packed_items = list(order_packed_items.get(order_row, []))
	return get_component_order_rows(
		doc, item_row.item_code, get_product_bundle_items_by_name(bundle_name), so_packed_items
	)


def get_kept_packed_items(doc):
	"""Yield (packed row, bundle row, stock qty per bundle unit) for each packed row of the last
	build that make_packing_list keeps for the bundle rows as they are now."""
	packed_items_table = get_indexed_packed_items_table(doc)
	order_packed_items = get_order_packed_items(doc)
	# only a bundle row that has packed rows can keep one
	parent_items = {row.parent_item for row in doc.get("packed_items")}
	for item_row in doc.get("items"):
		if item_row.item_code not in parent_items:
			continue

		if not (bundle_name := get_bundle_version_for_row(item_row, doc)):
			continue

		for bundle_item, so_packed_item in get_bundle_components(
			doc, item_row, bundle_name, order_packed_items
		):
			stale_rows = get_stale_packed_rows(
				doc,
				item_row,
				bundle_item,
				packed_items_table,
				get_sales_order_packed_item(doc, so_packed_item),
			)
			if stale_rows:
				packed_row = stale_rows.pop(0)
				yield (
					packed_row,
					item_row,
					get_component_stock_qty_per_unit(bundle_item, packed_row.uom, so_packed_item),
				)


>>>>>>> 3517ae7 (fix(stock): return each packed row of a bundle delivered from several warehouses)
def is_product_bundle(item_code: str) -> bool:
	return bool(frappe.db.exists("Product Bundle", {"new_item_code": item_code, "disabled": 0}))


def get_indexed_packed_items_table(doc):
	"""
	Create dict from stale packed items table like:
	{(Parent Item 1, Bundle Item 1, ae4b5678): [{...}], (key): [{value}]}

	Use: to quickly retrieve/check if row existed in table instead of looping n times.
	A component repeated on a bundle shares one key, so rows are kept as a list and
	consumed per occurrence rather than collapsed onto a single row.

	A new doc (e.g. mapped) has no link to its item rows yet, so its packed rows are
	consumed in order per parent item and component. This is only safe if the item rows
	need exactly these rows, e.g. no item row was removed after mapping.
	"""
	indexed_table = {}
	for packed_item in doc.get("packed_items"):
		key = (
			packed_item.parent_item,
			packed_item.item_code,
			None if doc.is_new() else packed_item.parent_detail_docname,
		)

		indexed_table.setdefault(key, []).append(packed_item)

	if doc.is_new():
		needed_counts = Counter(
			(item_row.item_code, bundle_item.item_code, None)
			for item_row in doc.get("items")
			for bundle_item in get_product_bundle_items(item_row.item_code)
		)
		indexed_table = {key: rows for key, rows in indexed_table.items() if len(rows) == needed_counts[key]}

	return indexed_table


def reset_packing_list(doc):
	"Conditionally reset the table and return if it was reset or not."
	reset_table = False
	doc_before_save = doc.get_doc_before_save()

	if doc_before_save:
		# reset table if:
		# 1. items were deleted
		# 2. if bundle item replaced by another item (same no. of items but different items)
		# we maintain list to track recurring item rows as well
		items_before_save = [(item.name, item.item_code) for item in doc_before_save.get("items")]
		items_after_save = [(item.name, item.item_code) for item in doc.get("items")]
		reset_table = items_before_save != items_after_save
	else:
		# reset: if via Update Items OR
		# if new mapped doc with packed items set (SO -> DN)
		# (cannot determine action)
		reset_table = True

	if reset_table:
		doc.set("packed_items", [])
	return reset_table


def get_product_bundle_items(item_code):
	product_bundle = frappe.qb.DocType("Product Bundle")
	product_bundle_item = frappe.qb.DocType("Product Bundle Item")

	query = (
		frappe.qb.from_(product_bundle_item)
		.join(product_bundle)
		.on(product_bundle_item.parent == product_bundle.name)
		.select(
			product_bundle_item.item_code,
			product_bundle_item.qty,
			product_bundle_item.uom,
			product_bundle_item.description,
		)
		.where((product_bundle.new_item_code == item_code) & (product_bundle.disabled == 0))
		.orderby(product_bundle_item.idx)
	)
	return query.run(as_dict=True)


<<<<<<< HEAD
def add_packed_item_row(doc, packing_item, main_item_row, packed_items_table, reset):
=======
def get_bundle_version_for_row(item_row, doc=None):
	"""Product Bundle version to pack ``item_row`` from.

	Honours a version explicitly chosen on the row (validated to be a submitted
	bundle of that item); otherwise falls back to the item's active version. A stale
	choice (e.g. left over after changing the item) self-heals back to the active
	one, but a disabled choice blocks the transaction instead of silently switching
	versions behind the user's back. A return reuses the exact version of the document
	it reverses, so a since-disabled version must not block it.
	"""
	from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle

	chosen = item_row.get("product_bundle") if item_row.meta.has_field("product_bundle") else None
	if chosen:
		bundle = frappe.db.get_value(
			"Product Bundle", chosen, ["new_item_code", "docstatus", "disabled"], as_dict=True
		)
		if bundle and bundle.new_item_code == item_row.item_code and bundle.docstatus == 1:
			if bundle.disabled and not (doc and doc.get("is_return")):
				frappe.throw(
					_("Row #{0}: Product Bundle {1} is disabled and cannot be used in transactions.").format(
						item_row.idx, frappe.bold(chosen)
					),
					title=_("Disabled Product Bundle"),
				)
			return chosen

	return get_active_product_bundle(item_row.item_code)


def add_packed_item_row(
	doc, packing_item, main_item_row, packed_items_table, reset, sales_order_packed_item=None, location=None
):
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)
	"""Add and return packed item row.
	doc: Transaction document
	packing_item (dict): Packed Item details
	main_item_row (dict): Items table row corresponding to packed item
	packed_items_table (dict): Packed Items table before save (indexed)
	reset (bool): State if table is reset or preserved as is
<<<<<<< HEAD
=======
	sales_order_packed_item (str): the Sales Order's packed row this row delivers
	location (dict): Pick List row the packed row is packed from
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)
	"""
	exists, pi_row = False, {}

	# check if row already exists in packed items table
	key = (
		main_item_row.item_code,
		packing_item.item_code,
		None if doc.is_new() else main_item_row.name,
	)
	# a component repeated on the bundle shares one key; consume stale rows in order so
	# each occurrence keeps its own packed row instead of overwriting a single one
<<<<<<< HEAD
	if stale_rows := packed_items_table.get(key):
		pi_row, exists = stale_rows.pop(0), True
=======
	if stale_rows := get_stale_packed_rows(
		doc, main_item_row, packing_item, packed_items_table, sales_order_packed_item
	):
		pi_row, exists = stale_rows.pop(get_stale_row_idx(stale_rows, location)), True
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)

	if not exists:
		pi_row = doc.append("packed_items", {})
	elif reset:  # add row if row exists but table is reset
		pi_row.idx = None
		if doc.is_new():
			pi_row.name = None
		pi_row = doc.append("packed_items", pi_row)

	return pi_row


<<<<<<< HEAD
=======
def get_stale_packed_rows(doc, main_item_row, packing_item, packed_items_table, sales_order_packed_item):
	"""Rows of the packed items table before save that ``main_item_row``'s component can reuse."""
	key = get_packed_item_key(
		doc, main_item_row, packing_item.item_code, packed_items_table, sales_order_packed_item
	)
	return packed_items_table.get(key)


def get_packed_item_key(doc, main_item_row, item_code, packed_items_table, sales_order_packed_item=None):
	# an unsaved row made from a Sales Order is found by its order packed row, since its idx
	# shifts when a row above it is deleted
	order_key = (main_item_row.item_code, item_code, sales_order_packed_item)
	if doc.is_new() and sales_order_packed_item and packed_items_table.get(order_key):
		return order_key

	return (main_item_row.item_code, item_code, main_item_row.idx if doc.is_new() else main_item_row.name)


def get_stale_row_idx(stale_rows, location=None):
	"""Index of the stale row packed from the Pick List row ``location``, else of the first one."""
	if not location:
		return 0
	return next((idx for idx, row in enumerate(stale_rows) if is_packed_from(row, location)), 0)


def is_packed_from(pi_row, location):
	"""Whether a packed row holds serial nos of the Pick List row ``location``, or its warehouse and batch."""
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	serial_nos = {number.lower() for number in get_serial_nos(pi_row.serial_no)}
	if serial_nos & {number.lower() for number in get_serial_nos(location.serial_no)}:
		return True
	return (pi_row.warehouse, pi_row.batch_no or "") == (location.warehouse, location.batch_no or "")


def remove_unused_pick_list_rows(doc, packed_items_table):
	"""Drop packed rows a re-save no longer packs from the Pick List, e.g. after the bundle qty is lowered."""
	pick_list_rows = {item.name for item in doc.get("items") if item.get("against_pick_list")}
	for rows in packed_items_table.values():
		for row in rows:
			if row.parent_detail_docname in pick_list_rows:
				doc.remove(row)


>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)
def get_packed_item_details(item_code, company):
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	query = (
		frappe.qb.from_(item)
		.left_join(item_default)
		.on((item_default.parent == item.name) & (item_default.company == company))
		.select(
			item.item_name,
			item.is_stock_item,
			item.description,
			item.stock_uom,
			item.valuation_rate,
			item_default.default_warehouse,
		)
		.where(item.name == item_code)
	)
	return query.run(as_dict=True)[0]


def update_packed_item_basic_data(main_item_row, pi_row, packing_item, item_data, so_packed_item=None):
	pi_row.parent_item = main_item_row.item_code
	pi_row.parent_detail_docname = main_item_row.name
	pi_row.item_code = packing_item.item_code
	pi_row.item_name = item_data.item_name
	pi_row.uom = item_data.stock_uom
	pi_row.qty = get_packed_qty(main_item_row, packing_item, item_data, so_packed_item)
	pi_row.conversion_factor = main_item_row.conversion_factor
	pi_row.delivered_by_supplier = main_item_row.get("delivered_by_supplier")

	if not pi_row.description:
		pi_row.description = packing_item.get("description")


def get_packed_qty(main_item_row, packing_item, item_data, so_packed_item=None):
	"""Component stock qty to pack for the bundle row."""
	return flt(
		get_component_stock_qty_per_unit(packing_item, item_data.stock_uom, so_packed_item)
		* flt(main_item_row.stock_qty),
		frappe.get_precision("Packed Item", "qty"),
	)


def get_component_stock_qty_per_unit(packing_item, stock_uom, so_packed_item=None):
	"""Component stock qty per bundle stock unit; a Sales Order's packed row keeps the qty it was ordered with."""
	if so_packed_item and so_packed_item.qty_per_unit:
		return so_packed_item.qty_per_unit

	# component qty is in the bundle row's UOM; convert to stock qty
	return flt(packing_item.qty) * get_component_conversion_factor(packing_item, stock_uom)


def get_order_packed_items(doc) -> dict:
	"""Packed rows of the rows this document is made from, by that row in idx order:
	the returned document's for a return, else the Sales Order's."""
	return get_packed_items_of_order_rows(
		{row for item in doc.get("items") if (row := get_order_row(doc, item))},
		doc.doctype if doc.get("is_return") else "Sales Order",
	)


def get_order_row(doc, item_row):
	"""Row whose packed rows ``item_row`` keeps the qty of."""
	if not doc.get("is_return"):
		return item_row.get("so_detail")
	return item_row.get(
		"dn_detail" if doc.doctype == "Delivery Note" else frappe.scrub(doc.doctype) + "_item"
	)


def get_packed_items_of_order_rows(order_rows, doctype="Sales Order") -> dict:
	"""Packed rows of the given rows of ``doctype``, by row in idx order."""
	if not order_rows:
		return {}

	packed_item = frappe.qb.DocType("Packed Item")
	order_item = frappe.qb.DocType(f"{doctype} Item")
	rows = (
		frappe.qb.from_(packed_item)
		.join(order_item)
		.on(order_item.name == packed_item.parent_detail_docname)
		.select(
			packed_item.name,
			packed_item.parent_detail_docname,
			packed_item.parent_item,
			packed_item.item_code,
			packed_item.qty,
			packed_item.picked_qty,
			order_item.stock_qty.as_("order_stock_qty"),
		)
		.where((packed_item.parenttype == doctype) & packed_item.parent_detail_docname.isin(list(order_rows)))
		.orderby(packed_item.idx)
		.run(as_dict=True)
	)

	order_packed_items = {}
	for row in rows:
		row.qty_per_unit = flt(row.qty) / flt(row.order_stock_qty) if flt(row.order_stock_qty) else 0
		order_packed_items.setdefault(row.parent_detail_docname, []).append(row)

	return order_packed_items


def pop_order_packed_item(so_packed_items, parent_item, item_code):
	"""Take the order's packed row of a component; a component repeated in the bundle takes the next one."""
	for idx, row in enumerate(so_packed_items):
		if row.parent_item == parent_item and row.item_code == item_code:
			return so_packed_items.pop(idx)


<<<<<<< HEAD
<<<<<<< HEAD
def get_component_conversion_factor(packing_item, stock_uom):
	uom = packing_item.get("uom")
	if not uom or uom == stock_uom:
		return 1.0
	return flt(get_conversion_factor(packing_item.item_code, uom).get("conversion_factor")) or 1.0

=======
=======
def get_component_order_rows(doc, parent_item, components, so_packed_items) -> list[tuple]:
	"""Each component of a bundle row with the order's packed row it packs.

	A return also packs every other returned row, e.g. of a component delivered from several warehouses."""
	rows = [
		(component, pop_order_packed_item(so_packed_items, parent_item, component.item_code))
		for component in components
	]
	if doc.get("is_return"):
		components_by_code = {component.item_code: component for component in components}
		rows.extend(
			(components_by_code[row.item_code], row)
			for row in so_packed_items
			if row.parent_item == parent_item and row.item_code in components_by_code
		)

	return rows


>>>>>>> 3517ae7 (fix(stock): return each packed row of a bundle delivered from several warehouses)
def get_order_packed_item_pairs(doc) -> list[tuple]:
	"""Pair each packed row of a document made from a Sales Order with the order's packed row it delivers."""
	order_packed_items = get_order_packed_items(doc)
	pairs = []
	for item in doc.get("items"):
		so_packed_items = list(order_packed_items.get(get_order_row(doc, item), []))
		paired = {}
		for packed_item in doc.get("packed_items"):
			if packed_item.parent_detail_docname != (item.name or item.idx):
				continue

			# a component packed from several Pick List locations delivers the same order row
			if so_packed_item := pop_order_packed_item(
				so_packed_items, packed_item.parent_item, packed_item.item_code
			) or paired.get(packed_item.item_code):
				paired[packed_item.item_code] = so_packed_item
				pairs.append((packed_item, so_packed_item))
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)

def update_packed_item_stock_data(main_item_row, pi_row, packing_item, item_data, doc):
	# TODO batch_no, actual_batch_qty, incoming_rate
	if not pi_row.warehouse and not doc.amended_from:
		fetch_warehouse = doc.get("is_pos") or item_data.is_stock_item or not item_data.default_warehouse
		pi_row.warehouse = (
			main_item_row.warehouse
			if (fetch_warehouse and main_item_row.warehouse)
			else item_data.default_warehouse
		)

	if not pi_row.target_warehouse:
		pi_row.target_warehouse = main_item_row.get("target_warehouse")

	bin = get_packed_item_bin_qty(packing_item.item_code, pi_row.warehouse)
	pi_row.actual_qty = flt(bin.get("actual_qty"))
	pi_row.projected_qty = flt(bin.get("projected_qty"))
	pi_row.use_serial_batch_fields = frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields")


def get_pick_list_locations(doc, main_item_row, packing_item, item_data, so_packed_item, packed_items_table):
	"""Pick List rows to pack a component from, each with its ``pack_qty``."""
	if not main_item_row.get("against_pick_list"):
		return []

	filters = {
<<<<<<< HEAD
		"item_code": pi_row.item_code,
		"sales_order": main_item_row.get("against_sales_order"),
=======
		"item_code": packing_item.item_code,
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)
		"sales_order_item": main_item_row.get("so_detail"),
		"parent": main_item_row.against_pick_list,
	}
	# a component repeated on the bundle has a pick list row per packed row
	if so_packed_item:
		filters["product_bundle_item"] = so_packed_item.name

	pl_rows = frappe.get_all(
		"Pick List Item",
		filters,
		["item_code", "warehouse", "batch_no", "serial_no", "picked_qty", "delivered_qty"],
		order_by="qty desc",
	)
	if not pl_rows:
		return []

	# a re-save keeps packing from the rows it packed from before
	key = get_packed_item_key(
		doc,
		main_item_row,
		packing_item.item_code,
		packed_items_table,
		get_sales_order_packed_item(doc, so_packed_item),
	)
	stale_rows = packed_items_table.get(key, [])
	pl_rows.sort(key=lambda row: not any(is_packed_from(stale_row, row) for stale_row in stale_rows))
	qty = get_packed_qty(main_item_row, packing_item, item_data, so_packed_item)
	return allocate_picked_qty(pl_rows, qty)

<<<<<<< HEAD
	pi_row.warehouse = pl_row.warehouse
	pi_row.batch_no = pl_row.batch_no
	pi_row.serial_no = get_packed_serial_nos(pi_row, pl_row)
=======

def allocate_picked_qty(pl_rows, qty):
	"""Pick List rows that pack ``qty``, each up to its undelivered picked qty; the rest goes on the last one."""
	precision = frappe.get_precision("Pick List Item", "delivered_qty")
	locations = []
	for row in pl_rows:
		row.pack_qty = min(flt(row.picked_qty - row.delivered_qty, precision), qty)
		if row.pack_qty > 0:
			locations.append(row)
			qty = flt(qty - row.pack_qty, precision)

	if not locations:
		pl_rows[0].pack_qty = 0
		locations = pl_rows[:1]

	locations[-1].pack_qty += qty
	return locations


def update_packed_item_with_pick_list_info(main_item_row, pi_row, location):
	# serial nos kept from another location are not in this one
	if not is_packed_from(pi_row, location):
		pi_row.serial_no = None

	pi_row.qty = flt(location.pack_qty, pi_row.precision("qty"))
	pi_row.warehouse = location.warehouse
	pi_row.batch_no = location.batch_no
	pi_row.serial_no = get_packed_serial_nos(main_item_row, pi_row, location)
>>>>>>> afff595 (fix(stock): pack a bundle component from each pick list location)


def get_packed_serial_nos(pi_row, pl_row):
	"""Serial nos kept on the packed row, topped up from the pick list row, up to the packed qty."""
	from erpnext.stock.doctype.pick_list.pick_list import get_pending_serial_nos, get_serial_nos_in_stock
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	serial_nos = get_serial_nos(pi_row.serial_no)
	qty = cint(pi_row.qty)
	if len(serial_nos) < qty and pl_row.serial_no:
		kept = {number.lower() for number in serial_nos}
		pending = get_serial_nos(get_pending_serial_nos(pl_row, get_serial_nos_in_stock([pl_row])))
		serial_nos += [number for number in pending if number.lower() not in kept]

	return "\n".join(serial_nos[:qty])


def update_packed_item_price_data(pi_row, item_data, doc):
	"Set price as per price list or from the Item master."
	if pi_row.rate:
		return

	item_doc = frappe.get_cached_doc("Item", pi_row.item_code)
	row_data = pi_row.as_dict().copy()
	row_data.update(
		{
			"company": doc.get("company"),
			"price_list": doc.get("selling_price_list"),
			"currency": doc.get("currency"),
			"conversion_rate": doc.get("conversion_rate"),
		}
	)
	if not row_data.get("transaction_date"):
		row_data.update({"transaction_date": doc.get("transaction_date")})

	rate = get_price_list_rate(row_data, item_doc).get("price_list_rate")

	pi_row.rate = rate or item_data.get("valuation_rate") or 0.0


def update_packed_item_from_cancelled_doc(main_item_row, packing_item, pi_row, doc):
	"Update packed item row details from cancelled doc into amended doc."
	prev_doc_packed_items_map = None
	if doc.amended_from:
		prev_doc_packed_items_map = get_cancelled_doc_packed_item_details(doc.packed_items)

	if prev_doc_packed_items_map and prev_doc_packed_items_map.get(
		(packing_item.item_code, main_item_row.item_code)
	):
		prev_doc_row = prev_doc_packed_items_map.get((packing_item.item_code, main_item_row.item_code))
		pi_row.batch_no = prev_doc_row[0].batch_no
		pi_row.serial_no = prev_doc_row[0].serial_no
		pi_row.warehouse = prev_doc_row[0].warehouse


def get_packed_item_bin_qty(item, warehouse):
	bin_data = frappe.db.get_values(
		"Bin",
		fieldname=["actual_qty", "projected_qty"],
		filters={"item_code": item, "warehouse": warehouse},
		as_dict=True,
	)

	return bin_data[0] if bin_data else {}


def get_cancelled_doc_packed_item_details(old_packed_items):
	prev_doc_packed_items_map = {}
	for items in old_packed_items:
		prev_doc_packed_items_map.setdefault((items.item_code, items.parent_item), []).append(items.as_dict())
	return prev_doc_packed_items_map


def update_product_bundle_rate(parent_items_price, pi_row, item_row):
	"""
	Update the price dict of Product Bundles based on the rates of the Items in the bundle.

	Stucture:
	{(Bundle Item 1, ae56fgji): 150.0, (Bundle Item 2, bc78fkjo): 200.0}
	"""
	key = (pi_row.parent_item, pi_row.parent_detail_docname)
	rate = parent_items_price.get(key)
	if not rate:
		parent_items_price[key] = 0.0

	parent_items_price[key] += flt((pi_row.rate * pi_row.qty) / item_row.stock_qty)


def set_product_bundle_rate_amount(doc, parent_items_price):
	"Set cumulative rate and amount in bundle item."
	rate_updated = False
	for item in doc.get("items"):
		bundle_rate = parent_items_price.get((item.item_code, item.name))
		if bundle_rate and bundle_rate != item.rate:
			item.rate = bundle_rate
			item.amount = flt(bundle_rate * item.qty)
			item.margin_rate_or_amount = 0
			item.discount_percentage = 0
			item.discount_amount = 0
			rate_updated = True
	if rate_updated:
		doc.calculate_taxes_and_totals()
		doc.set_total_in_words()


def on_doctype_update():
	frappe.db.add_index("Packed Item", ["item_code", "warehouse"])


@frappe.whitelist()
def get_items_from_product_bundle(row):
	row, items = json.loads(row), []

	bundled_items = get_product_bundle_items(row["item_code"])
	for item in bundled_items:
		row.update(
			{
				"item_code": item.item_code,
				# convert the component's bundle-row UOM to stock qty, as packing does
				"qty": flt(row["quantity"]) * flt(item.qty) * get_component_conversion_factor(item, None),
				"conversion_rate": 1,
				"currency": frappe.defaults.get_defaults().currency,
			}
		)
		items.append(get_item_details(row))

	return items
