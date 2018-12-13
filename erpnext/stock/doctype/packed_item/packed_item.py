# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import cstr, flt, cint
from erpnext.stock.get_item_details import get_item_details

from frappe.model.document import Document

class PackedItem(Document):
	pass

def get_product_bundle_items(item_code):
	return frappe.db.sql("""select t1.item_code, t1.qty, t1.uom, t1.description
		from `tabProduct Bundle Item` t1, `tabProduct Bundle` t2
		where t2.new_item_code=%s and t1.parent = t2.name order by t1.idx""", item_code, as_dict=1)

def get_current_product_bundle_items(item_code, name):
	cur_bundle = frappe.db.sql("""select pi.item_name, pi.item_code, pi.uom, pi.description, pi.qty
		from `tabPacked Item` pi 
		where pi.parent_item = %s and pi.parent_detail_docname= %s""",(item_code, name), as_dict=1)
	return cur_bundle

def get_packing_item_details(item, company):
	return frappe.db.sql("""
		select i.item_name, i.description, i.stock_uom, id.default_warehouse
		from `tabItem` i LEFT JOIN `tabItem Default` id ON id.parent=i.name and id.company=%s
		where i.name = %s""",
		(company, item), as_dict = 1)[0]

def get_bin_qty(item, warehouse):
	det = frappe.db.sql("""select actual_qty, projected_qty from `tabBin`
		where item_code = %s and warehouse = %s""", (item, warehouse), as_dict = 1)
	return det and det[0] or frappe._dict()

def update_packing_list_item(doc, packing_item_code, qty, main_item_row, description, packed_items_list):
	item = get_packing_item_details(packing_item_code, doc.company)

	# check if exists
	exists = 0
	for d in doc.get("packed_items"):
		if d.parent_item == main_item_row.item_code and d.item_code == packing_item_code and\
				d.parent_detail_docname == main_item_row.name and d.description == description:
			pi, exists = d, 1
			break

	if not exists:
		pi = doc.append('packed_items', {})

	pi.parent_item = main_item_row.item_code
	pi.item_code = packing_item_code
	pi.item_name = item.item_name
	pi.parent_detail_docname = main_item_row.name
	pi.description = item.description
	pi.uom = item.stock_uom
	pi.qty = flt(qty)
	pi.description = description
	if not pi.warehouse:
		pi.warehouse = (main_item_row.warehouse if ((doc.get('is_pos')
			or not item.default_warehouse) and main_item_row.warehouse) else item.default_warehouse)

	if not pi.batch_no:
		pi.batch_no = cstr(main_item_row.get("batch_no"))
	if not pi.target_warehouse:
		pi.target_warehouse = main_item_row.get("target_warehouse")
	bin = get_bin_qty(packing_item_code, pi.warehouse)
	pi.actual_qty = flt(bin.get("actual_qty"))
	pi.projected_qty = flt(bin.get("projected_qty"))
	packed_items_list.append(pi.idx)

def make_packing_list(doc, source_doctype=None, source_name=None):
	"""make packing list for Product Bundle item"""

	if doc.get("_action") and doc._action == "update_after_submit": return

	maintain_packed_items_list = 0
	if source_doctype is not None and source_doctype == "Sales Order":
		maintain_packed_items_list = cint(frappe.get_value(source_doctype, source_name, "maintain_packed_items_list"))
	else:
		if hasattr(doc, 'items'):
			if hasattr(doc.get("items")[0], 'against_sales_order'):
				maintain_packed_items_list = cint(frappe.get_value("Sales Order", doc.get("items")[0].against_sales_order,
				                                                   "maintain_packed_items_list"))

	if maintain_packed_items_list and doc.doctype == "Sales Order" and doc.docstatus != 0:
		return

	parent_items = []
	packed_items_list = []

	for d in doc.get("items"):
		if frappe.db.get_value("Product Bundle", {"new_item_code": d.item_code}):
			if maintain_packed_items_list and doc.doctype in ["Sales Invoice", "Delivery Note"] and d.so_detail is not None:
				for i in get_current_product_bundle_items(d.item_code, d.so_detail):
					update_packing_list_item(doc, i.item_code, flt(i.qty), d, i.description, packed_items_list)
			else:
				for i in get_product_bundle_items(d.item_code):
					update_packing_list_item(doc, i.item_code, flt(i.qty)*flt(d.stock_qty), d, i.description, packed_items_list)

			if [d.item_code, d.name] not in parent_items:
				parent_items.append([d.item_code, d.name])

	cleanup_packing_list(doc, parent_items, packed_items_list, maintain_packed_items_list)

def cleanup_packing_list(doc, parent_items, packed_items_list, maintain_packed_items_list):
	"""Remove all those child items which are no longer present in main item table"""
	delete_list = []
	for d in doc.get("packed_items"):
		if maintain_packed_items_list:
			if d.idx not in packed_items_list:
				# mark for deletion from doclist
				delete_list.append(d)
		else:
			if [d.parent_item, d.parent_detail_docname] not in parent_items:
				# mark for deletion from doclist
				delete_list.append(d)

	if not delete_list:
		return doc

	packed_items = doc.get("packed_items")
	doc.set("packed_items", [])
	# c is to keep the item starting from 1 in the packing list after save/submit a delivery note created from sales order,
	# otherwise it will increase through the number of items
	c = 1
	for d in packed_items:
		if d not in delete_list:
			d.idx = c
			c += 1
			doc.append("packed_items", d)

@frappe.whitelist()
def get_items_from_product_bundle(args):
	args = json.loads(args)
	items = []
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
