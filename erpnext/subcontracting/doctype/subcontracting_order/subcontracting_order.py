# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.utils import get_bin


class SubcontractingOrder(SubcontractingController):
	def validate(self):
		super(SubcontractingOrder, self).validate()
		self.validate_reserve_warehouse()

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		self.update_reserved_qty_for_subcontract()
		self.notify_update()
		clear_doctype_notifications(self)

	def check_modified_date(self):
		mod_db = frappe.db.sql("select modified from `tabSubcontracting Order` where name = %s",
			self.name)
		date_diff = frappe.db.sql("select '%s' - '%s' " % (mod_db[0][0], frappe.utils.cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			frappe.msgprint(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name),
				raise_exception=True)

	def update_reserved_qty_for_subcontract(self):
		for d in self.supplied_items:
			if d.rm_item_code:
				stock_bin = get_bin(d.rm_item_code, d.reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

@frappe.whitelist()
def make_subcontracting_receipt(source_name, target_doc=None):
	return get_mapped_subcontracting_receipt(source_name, target_doc)

def get_mapped_subcontracting_receipt(source_name, target_doc=None):
	doc = get_mapped_doc("Subcontracting Order", source_name,	{
		"Subcontracting Order": {
			"doctype": "Subcontracting Receipt",
			"field_map": {
			},
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Subcontracting Order Service Item": {
			"doctype": "Subcontracting Receipt Service Item",
		},
		"Subcontracting Order Finished Good Item": {
			"doctype": "Subcontracting Receipt Finished Good Item",
		},
		"Subcontracting Order Supplied Item": {
			"doctype": "Subcontracting Receipt Supplied Item",
		},
	}, target_doc)

	return doc

@frappe.whitelist()
def get_materials_from_supplier(subcontracting_order, sco_details):
	if isinstance(sco_details, str):
		sco_details = json.loads(sco_details)

	doc = frappe.get_cached_doc('Subcontracting Order', subcontracting_order)
	doc.initialized_fields()
	doc.subcontracting_orders = [doc.name]
	doc.get_available_materials()

	if not doc.available_materials:
		frappe.throw(_('Materials are already received against the Subcontracting Order {0}')
			.format(subcontracting_order))

	return make_return_stock_entry_for_subcontract(doc.available_materials, doc, sco_details)

def get_item_details(items):
	item_details = {}
	for d in frappe.db.sql("""select item_code, description, allow_alternative_item from `tabItem`
		where name in ({0})""".format(", ".join(["%s"] * len(items))), items, as_dict=1):
		item_details[d.item_code] = d

	return item_details

@frappe.whitelist()
def make_rm_stock_entry(subcontracting_order, rm_items):
	rm_items_list = rm_items

	if isinstance(rm_items, str):
		rm_items_list = json.loads(rm_items)
	elif not rm_items:
		frappe.throw(_("No Items available for transfer"))

	if rm_items_list:
		fg_items = list(set(d["item_code"] for d in rm_items_list))
	else:
		frappe.throw(_("No Items selected for transfer"))

	if subcontracting_order:
		subcontracting_order = frappe.get_doc("Subcontracting Order", subcontracting_order)

	if fg_items:
		items = tuple(set(d["rm_item_code"] for d in rm_items_list))
		item_wh = get_item_details(items)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Send to Subcontractor"
		stock_entry.subcontracting_order = subcontracting_order.name
		stock_entry.supplier = subcontracting_order.supplier
		stock_entry.supplier_name = subcontracting_order.supplier_name
		stock_entry.supplier_address = subcontracting_order.supplier_address
		stock_entry.address_display = subcontracting_order.address_display
		stock_entry.company = subcontracting_order.company
		stock_entry.to_warehouse = subcontracting_order.supplier_warehouse
		stock_entry.set_stock_entry_type()

		for item_code in fg_items:
			for rm_item_data in rm_items_list:
				if rm_item_data["item_code"] == item_code:
					rm_item_code = rm_item_data["rm_item_code"]
					items_dict = {
						rm_item_code: {
							"sco_detail": rm_item_data.get("name"),
							"item_name": rm_item_data["item_name"],
							"description": item_wh.get(rm_item_code, {}).get('description', ""),
							'qty': rm_item_data["qty"],
							'from_warehouse': rm_item_data["warehouse"],
							'stock_uom': rm_item_data["stock_uom"],
							'serial_no': rm_item_data.get('serial_no'),
							'batch_no': rm_item_data.get('batch_no'),
							'main_item_code': rm_item_data["item_code"],
							'allow_alternative_item': item_wh.get(rm_item_code, {}).get('allow_alternative_item')
						}
					}
					stock_entry.add_to_stock_entry_detail(items_dict)
		return stock_entry.as_dict()
	else:
		frappe.throw(_("No Items selected for transfer"))
	return subcontracting_order.name

def make_return_stock_entry_for_subcontract(available_materials, sco_doc, sco_details):
	ste_doc = frappe.new_doc('Stock Entry')
	ste_doc.purpose = 'Material Transfer'
	ste_doc.subcontracting_order = sco_doc.name
	ste_doc.company = sco_doc.company
	ste_doc.is_return = 1

	for key, value in available_materials.items():
		if not value.qty:
			continue

		if value.batch_no:
			for batch_no, qty in value.batch_no.items():
				if qty > 0:
					add_items_in_ste(ste_doc, value, value.qty, sco_details, batch_no)
		else:
			add_items_in_ste(ste_doc, value, value.qty, sco_details)

	ste_doc.set_stock_entry_type()
	ste_doc.calculate_rate_and_amount()

	return ste_doc

def add_items_in_ste(ste_doc, row, qty, sco_details, batch_no=None):
	item = ste_doc.append('items', row.item_details)
	sco_detail = list(set(row.sco_details).intersection(sco_details))
	item.update({
		'qty': qty,
		'batch_no': batch_no,
		'basic_rate': row.item_details['rate'],
		'sco_detail': sco_detail[0] if sco_detail else '',
		's_warehouse': row.item_details['t_warehouse'],
		't_warehouse': row.item_details['s_warehouse'],
		'item_code': row.item_details['rm_item_code'],
		'subcontracted_item': row.item_details['main_item_code'],
		'serial_no': '\n'.join(row.serial_no) if row.serial_no else ''
	})