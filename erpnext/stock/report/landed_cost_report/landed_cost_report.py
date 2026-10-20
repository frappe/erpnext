# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

import erpnext


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
			"label": _("Landed Cost"),
			"fieldname": "landed_cost",
			"fieldtype": "Currency",
			"options": "currency",
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{
			"label": _("Purchase Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
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
	company_currency = erpnext.get_company_currency(filters.get("company"))
	landed_cost_vouchers = get_landed_cost_vouchers(filters) or {}
	landed_vouchers = list(landed_cost_vouchers.keys())
	vendor_invoices = {}
	if landed_vouchers:
		vendor_invoices = get_vendor_invoices(landed_vouchers)

	data = []

	for name, vouchers in landed_cost_vouchers.items():
		res = {
			"name": name,
		}

		for i, d in enumerate(vouchers):
			if i:
				res = {}

			res.update(
				{
					"landed_cost": d.landed_cost,
					"voucher_type": d.voucher_type,
					"voucher_no": d.voucher_no,
					"currency": company_currency,
				}
			)

			data.append(res)

		for vendor_invoice in vendor_invoices.get(name, []):
			data.append({"vendor_invoice": vendor_invoice})

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
			lcv_voucher.receipt_document_type.as_("voucher_type"),
			lcv_voucher.receipt_document.as_("voucher_no"),
		)
		.where((lcv.docstatus == 1) & (lcv.company == filters.company))
		.orderby(lcv.name)
		.orderby(lcv_voucher.idx)
	)

	if filters.from_date and filters.to_date:
		query = query.where(lcv.posting_date.between(filters.from_date, filters.to_date))

	if filters.raw_material_voucher_type:
		query = query.where(lcv_voucher.receipt_document_type == filters.raw_material_voucher_type)

	if filters.raw_material_voucher_no:
		query = query.where(lcv_voucher.receipt_document == filters.raw_material_voucher_no)

	data = query.run(as_dict=True) or []
	allocations = get_receipt_allocations({row.name for row in data})
	result = {}
	for row in data:
		row.landed_cost = allocations.get((row.name, row.voucher_type, row.voucher_no), 0.0)
		result.setdefault((row.name), []).append(row)

	return result


def get_receipt_allocations(landed_vouchers):
	if not landed_vouchers:
		return {}

	item = frappe.qb.DocType("Landed Cost Item")
	rows = (
		frappe.qb.from_(item)
		.select(item.parent, item.receipt_document_type, item.receipt_document, Sum(item.applicable_charges))
		.where(item.parent.isin(landed_vouchers))
		.groupby(item.parent, item.receipt_document_type, item.receipt_document)
	).run()

	return {(parent, doctype, name): flt(amount) for parent, doctype, name, amount in rows}


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
