# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.subcontracting import Subcontracting


class SubcontractingOrder(Document, Subcontracting):
	def validate(self):
		self.validate_purchase_order()

	def validate_purchase_order(self):
		if self.get("purchase_order"):
			po = frappe.get_doc("Purchase Order", self.get("purchase_order"))

			if po.docstatus != 1:
				msg = f"Please submit Purchase Order {po.name} before proceeding."
				frappe.throw(_(msg))

			if po.is_subcontracted != "Yes":
				frappe.throw(_("Please select a valid Purchase Order that is configured for Subcontracting."))
		else:
			self.service_items = None


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