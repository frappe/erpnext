# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.doctype.address.address import get_company_address

# from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, flt

from erpnext.controllers.selling_controller import SellingController
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults


class ProformaInvoice(SellingController):
	def __init__(self, *args, **kwargs):
		super(ProformaInvoice, self).__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Proforma Invoice Item",
				"target_dt": "Sales Order Item",
				"target_field": "proforma_qty",  # field of Sales Order Item
				"source_field": "qty",  # field of Proforma Invoice Item
				"target_ref_field": "qty",  # field of Proforma Invoice Item
				"join_field": "so_item",  # field of Proforma Invoice Item
				"target_parent_dt": "Sales Order",
				"percent_join_field": "sales_order",
			}
		]

	# def before_save(self):
	# 	total_rate = 0
	# 	total_qty = 0
	# 	total = 0

	# 	for d in self.items:
	# 		total_qty += flt(d.qty)
	# 		total_rate += flt(d.rate)
	# 		total += flt(d.qty) * flt(d.rate)
	# 		d.amount = flt(d.qty) * flt(d.rate)
	# 		q = frappe.db.get_all(
	# 			"Sales Order Item",
	# 			filters={"name":d.so_item,"parent":d.sales_order},
	# 			fields=["qty"],
	# 		)
	# 		print("REMM",d.so_item,d.sales_order,d.rem_qty,q)
	# 		# d.rem_qty = flt(q[0]['qty']) - flt(d.qty)

	# 		if d.rem_qty:
	# 			d.rem_qty -= d.qty

	# 		elif d.qty > q[0]['qty']:
	# 				frappe.throw(_(f"Quantity unavailable at row {d.idx}"))

	# 		else:
	# 			d.rem_qty = flt(q[0]['qty']) - flt(d.qty)

	# 	self.total_qty = total_qty
	# 	self.base_total = total

	def on_submit(self):
		self.update_prevdoc_status()


@frappe.whitelist()
def make_delivery_note_against_proforma_invoice(
	source_name, target_doc=None, ignore_permissions=False
):
	def postprocess(source, target):
		# set_missing_values(source, target)
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		# target.run_method("set_missing_values")
		# target.run_method("set_po_nos")
		target.run_method("cos")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		# make_packing_list(target)

	def update_item(source, target, source_parent):
		# print(source)
		target.delivery_date = source.delivery_date
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)
		# target.qty = flt(source.qty) - flt(source.proforma_qty)

		if target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	doclist = get_mapped_doc(
		"Proforma Invoice",
		source_name,
		{
			"Proforma Invoice": {
				"doctype": "Delivery Note",
				"field_map": {"delivery_date": "delivery_date"},
			},
			"Proforma Invoice Item": {
				"doctype": "Delivery Note Item",
				"field_map": {
					# Proforma Invoice Item field name : DN Item field name
					"so_item": "so_detail",
					"sales_order": "against_sales_order",
					"name": "pi_item",
					"parent": "proforma_invoice",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.qty,
			},
		},
		target_doc,
		postprocess,
		# ignore_permissions=ignore_permissions,
	)

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	doclist.set_onload("ignore_price_list", True)

	return doclist
