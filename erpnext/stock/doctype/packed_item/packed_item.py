# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt


import json

import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt

from erpnext.stock.get_item_details import get_item_details


class PackedItem(Document):
	pass

def make_packing_list(doc):
	"""make packing list for Product Bundle item"""
	if doc.get("_action") and doc._action == "update_after_submit":
		return

	if not doc.is_new():
		reset_packing_list_if_deleted_items_exist(doc)

	parent_items = []
	for item in doc.get("items"):
		if frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
			for bundle_item in get_product_bundle_items(item.item_code):
				update_packing_list_item(
					doc=doc, packing_item_code=bundle_item.item_code,
					qty=flt(bundle_item.qty) * flt(item.stock_qty),
					main_item_row=item, description=bundle_item.description
				)

			if [item.item_code, item.name] not in parent_items:
				parent_items.append([item.item_code, item.name])

	if frappe.db.get_single_value("Selling Settings", "editable_bundle_item_rates"):
		update_product_bundle_price(doc, parent_items)

def reset_packing_list_if_deleted_items_exist(doc):
	doc_before_save = doc.get_doc_before_save()
	if doc_before_save:
		items_are_deleted = len(doc_before_save.get("items")) != len(doc.get("items"))
	else:
		items_are_deleted = True

	if items_are_deleted:
		doc.set("packed_items", [])

def get_product_bundle_items(item_code):
	product_bundle = frappe.qb.DocType("Product Bundle")
	product_bundle_item = frappe.qb.DocType("Product Bundle Item")

	query = (
		frappe.qb.from_(product_bundle_item)
		.join(product_bundle).on(product_bundle_item.parent == product_bundle.name)
		.select(
			product_bundle_item.item_code,
			product_bundle_item.qty,
			product_bundle_item.uom,
			product_bundle_item.description
		).where(
			product_bundle.new_item_code == item_code
		).orderby(
			product_bundle_item.idx
		)
	)
	return query.run(as_dict=True)

def update_packing_list_item(doc, packing_item_code, qty, main_item_row, description):
	old_packed_items_map = None

	if doc.amended_from:
		old_packed_items_map = get_old_packed_item_details(doc.packed_items)

	item = get_packing_item_details(packing_item_code, doc.company)

	# check if exists
	exists = 0
	for d in doc.get("packed_items"):
		if (d.parent_item == main_item_row.item_code and
			d.item_code == packing_item_code and
			d.parent_detail_docname == main_item_row.name
		):
			pi, exists = d, 1
			break

	if not exists:
		pi = doc.append('packed_items', {})

	pi.parent_item = main_item_row.item_code
	pi.item_code = packing_item_code
	pi.item_name = item.item_name
	pi.parent_detail_docname = main_item_row.name
	pi.uom = item.stock_uom
	pi.qty = flt(qty)
	pi.conversion_factor = main_item_row.conversion_factor
	if description and not pi.description:
		pi.description = description
	if not pi.warehouse and not doc.amended_from:
		pi.warehouse = (main_item_row.warehouse if ((doc.get('is_pos') or item.is_stock_item \
			or not item.default_warehouse) and main_item_row.warehouse) else item.default_warehouse)
	if not pi.batch_no and not doc.amended_from:
		pi.batch_no = cstr(main_item_row.get("batch_no"))
	if not pi.target_warehouse:
		pi.target_warehouse = main_item_row.get("target_warehouse")
	bin = get_packed_item_bin_qty(packing_item_code, pi.warehouse)
	pi.actual_qty = flt(bin.get("actual_qty"))
	pi.projected_qty = flt(bin.get("projected_qty"))
	if old_packed_items_map and old_packed_items_map.get((packing_item_code, main_item_row.item_code)):
		pi.batch_no = old_packed_items_map.get((packing_item_code, main_item_row.item_code))[0].batch_no
		pi.serial_no = old_packed_items_map.get((packing_item_code, main_item_row.item_code))[0].serial_no
		pi.warehouse = old_packed_items_map.get((packing_item_code, main_item_row.item_code))[0].warehouse

def get_packing_item_details(item_code, company):
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	query = (
		frappe.qb.from_(item)
		.left_join(item_default)
		.on(
			(item_default.parent == item.name)
			& (item_default.company == company)
		).select(
			item.item_name, item.is_stock_item,
			item.description, item.stock_uom,
			item_default.default_warehouse
		).where(
			item.name == item_code
		)
	)
	return query.run(as_dict=True)[0]

def get_packed_item_bin_qty(item, warehouse):
	bin_data = frappe.db.get_values(
		"Bin",
		fieldname=["actual_qty", "projected_qty"],
		filters={"item_code": item, "warehouse": warehouse},
		as_dict=True
	)

	return bin_data[0] if bin_data else {}

def get_old_packed_item_details(old_packed_items):
	old_packed_items_map = {}
	for items in old_packed_items:
		old_packed_items_map.setdefault((items.item_code ,items.parent_item), []).append(items.as_dict())
	return old_packed_items_map

def add_item_to_packing_list(doc, packed_item):
	doc.append("packed_items", {
		'parent_item': packed_item.parent_item,
		'item_code': packed_item.item_code,
		'item_name': packed_item.item_name,
		'uom': packed_item.uom,
		'qty': packed_item.qty,
		'rate': packed_item.rate,
		'conversion_factor': packed_item.conversion_factor,
		'description': packed_item.description,
		'warehouse': packed_item.warehouse,
		'batch_no': packed_item.batch_no,
		'actual_batch_qty': packed_item.actual_batch_qty,
		'serial_no': packed_item.serial_no,
		'target_warehouse': packed_item.target_warehouse,
		'actual_qty': packed_item.actual_qty,
		'projected_qty': packed_item.projected_qty,
		'incoming_rate': packed_item.incoming_rate,
		'prevdoc_doctype': packed_item.prevdoc_doctype,
		'parent_detail_docname': packed_item.parent_detail_docname
	})

def update_product_bundle_price(doc, parent_items):
	"""Updates the prices of Product Bundles based on the rates of the Items in the bundle."""

	if not doc.get('items'):
		return

	parent_items_index = 0
	bundle_price = 0

	for bundle_item in doc.get("packed_items"):
		if parent_items[parent_items_index][0] == bundle_item.parent_item:
			bundle_item_rate = bundle_item.rate if bundle_item.rate else 0
			bundle_price += bundle_item.qty * bundle_item_rate
		else:
			update_parent_item_price(doc, parent_items[parent_items_index][0], bundle_price)

			bundle_item_rate = bundle_item.rate if bundle_item.rate else 0
			bundle_price = bundle_item.qty * bundle_item_rate
			parent_items_index += 1

	# for the last product bundle
	if doc.get("packed_items"):
		update_parent_item_price(doc, parent_items[parent_items_index][0], bundle_price)

def update_parent_item_price(doc, parent_item_code, bundle_price):
	parent_item_doc = doc.get('items', {'item_code': parent_item_code})[0]

	current_parent_item_price = parent_item_doc.amount
	if current_parent_item_price != bundle_price:
		parent_item_doc.amount = bundle_price
		parent_item_doc.rate = bundle_price/(parent_item_doc.qty or 1)

@frappe.whitelist()
def get_items_from_product_bundle(args):
	args, items = json.loads(args), []

	bundled_items = get_product_bundle_items(args["item_code"])
	for item in bundled_items:
		args.update({
			"item_code": item.item_code,
			"qty": flt(args["quantity"]) * flt(item.qty)
		})
		items.append(get_item_details(args))

	return items

def on_doctype_update():
	frappe.db.add_index("Packed Item", ["item_code", "warehouse"])

