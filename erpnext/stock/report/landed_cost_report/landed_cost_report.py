# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Landed Cost Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Landed Cost Voucher",
		},
		{
			"label": _("Total Landed Cost"),
			"fieldname": "landed_cost",
			"fieldtype": "Currency",
		},
		{
			"label": _("Purchase Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Purchase Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 220,
		},
		{
			"label": _("Vendor Invoice"),
			"fieldname": "vendor_invoice",
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"width": 200,
		},
	]


def get_data(filters) -> list[list]:
	landed_cost_vouchers = get_landed_cost_vouchers(filters) or {}
	landed_vouchers = list(landed_cost_vouchers.keys())
	vendor_invoices = {}
	if landed_vouchers:
		vendor_invoices = get_vendor_invoices(landed_vouchers)

	data = []

	print(vendor_invoices)
	for name, vouchers in landed_cost_vouchers.items():
		res = {
			"name": name,
		}

		last_index = 0
		vendor_invoice_list = vendor_invoices.get(name, [])
		for i, d in enumerate(vouchers):
			if i == 0:
				res.update(
					{
						"landed_cost": d.landed_cost,
						"voucher_type": d.voucher_type,
						"voucher_no": d.voucher_no,
					}
				)
			else:
				res = {
					"voucher_type": d.voucher_type,
					"voucher_no": d.voucher_no,
				}

			if len(vendor_invoice_list) > i:
				res["vendor_invoice"] = vendor_invoice_list[i]

			data.append(res)
			last_index = i

		if vendor_invoice_list and len(vendor_invoice_list) > len(vouchers):
			for row in vendor_invoice_list[last_index + 1 :]:
				print(row)
				data.append({"vendor_invoice": row})

	return data


def get_landed_cost_vouchers(filters):
	lcv = frappe.qb.DocType("Landed Cost Voucher")
	lcv_voucher = frappe.qb.DocType("Landed Cost Purchase Receipt")

	query = (
		frappe.qb.from_(lcv)
		.inner_join(lcv_voucher)
		.on(lcv.name == lcv_voucher.parent)
		.select(
			lcv.name,
			lcv.total_taxes_and_charges.as_("landed_cost"),
			lcv_voucher.receipt_document_type.as_("voucher_type"),
			lcv_voucher.receipt_document.as_("voucher_no"),
		)
		.where((lcv.docstatus == 1) & (lcv.company == filters.company))
	)

	if filters.from_date and filters.to_date:
		query = query.where(lcv.posting_date.between(filters.from_date, filters.to_date))

	if filters.raw_material_voucher_type:
		query = query.where(lcv_voucher.receipt_document_type == filters.raw_material_voucher_type)

	if filters.raw_material_voucher_no:
		query = query.where(lcv_voucher.receipt_document == filters.raw_material_voucher_no)

	data = query.run(as_dict=True) or []
	result = {}
	for row in data:
		result.setdefault((row.name), []).append(row)

	return result


def get_vendor_invoices(landed_vouchers):
	doctype = frappe.qb.DocType("Landed Cost Vendor Invoice")

	query = (
		frappe.qb.from_(doctype)
		.select(
			doctype.parent,
			doctype.vendor_invoice,
		)
		.where((doctype.docstatus == 1) & (doctype.parent.isin(landed_vouchers)))
		.orderby(
			doctype.idx,
		)
	)

	data = query.run(as_dict=True) or []

	result = {}
	for row in data:
		result.setdefault(row.parent, []).append(row.vendor_invoice)

	return result
