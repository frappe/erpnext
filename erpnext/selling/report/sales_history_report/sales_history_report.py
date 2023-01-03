# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, qb
from frappe.query_builder import DocType
from frappe.utils import flt, getdate

def execute(filters=None):
	if not filters:
		filters = {}

	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_columns(data):
	columns = [
		{ "label": _("Sales Order"), "fieldtype": "Link", "fieldname": "sales_no", "options": "Sales Order", "width": 180, },
		{ "label": _("SO Date"), "fieldtype": "Date", "fieldname": "sales_date", "width": 100, },
		{ "label": _("Customer"), "fieldtype": "Link", "fieldname": "customer", "options": "Customer", "width": 180, },
		{ "label": _("Dispatch"), "fieldname": "dispatch", "fieldtype": "Data", "width": 100 },
		{ "label": _("SO Qty"), "fieldtype": "Data", "fieldname": "qty", "width": 100, },
		{ "label": _("Sales Price"), "fieldtype": "Currency", "fieldname": "so_rate", "width": 120, },
		{ "label": _("Sales Order Amount"), "fieldtype": "Currency", "fieldname": "so_amount", "width": 180, },
		{ "label": _("Item Code"), "fieldtype": "Link", "fieldname": "item_code", "options": "Item", "width": 120, },
		{ "label": _("Item Name"), "fieldtype": "Data", "fieldname": "item_name", "width": 120, },
		{ "label": _("UoM"), "fieldtype": "Link", "fieldname": "stock_uom", "options": "UOM", "width": 60, },
		{ "label": _("Item Type"), "fieldtype": "Data", "fieldname": "item_type", "width": 120, },
		{ "label": _("Warehouse"), "fieldtype": "Link", "fieldname": "warehouse", "options": "Warehouse", "width": 160, },
		{ "label": _("Delivery No"), "fieldtype": "Link", "fieldname": "dn_name", "options": "Delivery Note", "width": 170, },
		{ "label": _("Delivery Date"), "fieldtype": "Date", "fieldname": "dn_date", "width": 120, },
		{ "label": _("Delivered Qty"), "fieldtype": "Data", "fieldname": "delivered_qty", "width": 120, },
		{ "label": _("Invoice No"), "fieldtype": "Link", "fieldname": "si_no", "options": "Sales Invoice", "width": 180, },
		{ "label": _("Invoice Date"), "fieldtype": "Date", "fieldname": "si_date", "width": 120, },
		{ "label": _("Reference Date"), "fieldtype": "Date", "fieldname": "ref_date", "width": 120, },
		{ "label": _("Due Date"), "fieldtype": "Date", "fieldname": "due_date", "width": 120, },
		{ "label": _("Accepted Qty"), "fieldtype": "Data", "fieldname": "accepted_qty", "width": 120, },
		{ "label": _("Bill Amount"), "fieldtype": "Currency", "fieldname": "si_amount", "width": 180, },
		{ "label": _("Other Charges"), "fieldtype": "Currency", "fieldname": "other_charges", "width": 180, },
		{ "label": _("NL Qty"), "fieldtype": "Data", "fieldname": "nl_qty", "width": 80, },
		{ "label": _("NL Amoubt"), "fieldtype": "Currency", "fieldname": "nl_amt", "width": 120, },
		{ "label": _("ANL Qty"), "fieldtype": "Data", "fieldname": "anl_qty", "width": 80, },
		{ "label": _("ANL Amount"), "fieldtype": "Currency", "fieldname": "anl_amt", "width": 120, },
		{ "label": _("Excess Qty"), "fieldtype": "Data", "fieldname": "excess_qty", "width": 80, },
		{ "label": _("Excess Amount"), "fieldtype": "Currency", "fieldname": "excess_amt", "width": 120, },
		{ "label": _("Total Bill Amount"), "fieldtype": "Currency", "fieldname": "total_biiled_amt", "width": 180, },
		{ "label": _("Transporter Name"), "fieldtype": "Data", "fieldname": "transporter_name", "width": 150, },
		{ "label": _("Equipment Number"), "fieldtype": "Data", "fieldname": "equipment_no", "width": 120, },
		{ "label": _("Total Advance"), "fieldtype": "Currency", "fieldname": "total_advance", "width": 120, },
		{ "label": _("Location"), "fieldtype": "Data", "fieldname": "location", "width": 120, },
		{ "label": _("Penalties"), "fieldtype": "Data", "fieldname": "penalties", "width": 120, },
		{ "label": _("Penalties Remarks"), "fieldtype": "Data", "fieldname": "penalties_remarks", "width": 120, },
	]
	return columns

def get_data(filters):
	so = frappe.qb.DocType('Sales Order')
	so_item = frappe.qb.DocType('Sales Order Item')
	dn = frappe.qb.DocType('Delivery Note')
	dn_item = frappe.qb.DocType('Delivery Note Item')
	si = frappe.qb.DocType('Sales Invoice')
	si_item = frappe.qb.DocType('Sales Invoice Item')
	equip = frappe.qb.DocType('Equipment')

	query = (
		frappe.qb.from_(so)
		.inner_join(so_item)
		.on(so.name == so_item.parent)
		.left_join(dn_item)
		.on(dn_item.against_sales_order == so.name)
		.left_join(dn)
		.on(dn_item.parent == dn.name)
		.left_join(si_item)
		.on(si_item.delivery_note == dn.name)
		.left_join(si)
		.on(si_item.parent == si.name)
		.left_join(equip)
		.on(equip.name == dn_item.equipment)
		.select(
			so.name, so.transaction_date, so.customer, so.dispatch, so_item.qty, (so_item.rate.as_("so_rate")), (so_item.base_net_amount).as_("so_amount"), so_item.item_code, so_item.item_name, dn_item.item_type, so_item.uom, so_item.warehouse, (dn.name).as_("dn_name"), (dn.posting_date.as_("dn_date")), (dn_item.qty).as_("delivered_qty"), dn_item.others_equipment, dn_item.vehicle_number, dn_item.equipment, equip.supplier, dn_item.location, (si.name).as_("si_no"), (si.posting_date).as_("si_date"), si.due_date, si.total_advance, (si_item.accepted_qty).as_("accepted_qty"), (si_item.base_net_amount).as_("si_amount"), si_item.normal_loss, si_item.normal_loss_amt, si_item.abnormal_loss, si_item.abnormal_loss_amt, si_item.excess_qty, si_item.excess_amt, si.total_charges, si.grand_total
		)
		.where((so.docstatus == 1) & (dn.docstatus == 1) & (si.docstatus == 1))
	)

	if filters.get("customer"):
		query = (query.where(so.customer == filters.customer)) 
	if filters.get("from_date") and filters.get("to_date"):
		if filters.get("from_date") > filters.get("to_date"):
			frappe.throw('Enter From Date less than To Date')
		query = (query.where(filters.from_date <= so.transaction_date <=  filters.to_date))

	query = query.run(as_dict=True)

	data = []

	if query:
		for a in query:
			total_biiled_amt = flt(a.si_amount) + flt(a.total_charges) + flt(a.excess_amt) - flt(a.normal_loss_amt) - flt(a.abnormal_loss_amt)

			row = {
				"sales_no": a.name,
				"sales_date": a.transaction_date,
				"customer": a.customer,
				"dispatch": a.dispatch,
				"qty": a.qty,
				"so_rate": a.so_rate,
				"so_amount": a.so_amount,
				"item_code": a.item_code,
				"item_name": a.item_name,
				"stock_uom": a.uom,
				"item_type": a.item_type,
				"warehouse": a.warehouse,
				"total_advance": a.total_advance,
				"dn_name": a.dn_name,
				"dn_date": a.dn_date,
				"delivered_qty": a.delivered_qty,
				"si_no": a.si_no,
				"si_date": a.si_date,
				"ref_date": a.si_date,
				"due_date": a.due_date,
				"accepted_qty": a.accepted_qty,
				"si_amount": a.si_amount,
				"other_charges": a.total_charges,
				"nl_qty": a.normal_loss,
				"nl_amt": a.normal_loss_amt,
				"anl_qty": a.abnormal_loss,
				"anl_amt": a.abnormal_loss_amt,
				"excess_qty": a.excess_qty,
				"excess_amt": a.excess_amt,
				"transporter_name": a.supplier,
				"equipment_no": a.vehicle_number if flt(a.others_equipment) == 1 else a.equipment,
				"bill_amount": a.si_amount,
				"total_biiled_amt": total_biiled_amt,
				"location": a.location,
			}
			data.append(row)
	return data