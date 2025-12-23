# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull


def execute(filters=None):
	"""Generate Tax Withholding Details report"""
	validate_filters(filters)

	# Process and format data
	data = get_tax_withholding_data(filters)
	columns = get_columns(filters)

	return columns, data


def validate_filters(filters):
	"""Validate report filters"""
	filters = frappe._dict(filters or {})

	if not filters.from_date or not filters.to_date:
		frappe.throw(_("From Date and To Date are required"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))


def get_tax_withholding_data(filters):
	"""Process entries into final report format"""
	data = []
	entries = get_tax_withholding_entries(filters)
	if not entries:
		return data

	doc_info = get_additional_doc_info(entries)
	party_details = get_party_details(entries)

	for entry in entries:
		doc_details = frappe._dict()
		if entry.taxable_name:
			doc_details = doc_info.get((entry.taxable_doctype, entry.taxable_name), {})

		party_info = party_details.get((entry.party_type, entry.party), {})

		row = {
			"section_code": entry.tax_withholding_category,
			"entity_type": party_info.get("entity_type"),
			"rate": entry.tax_rate,
			"total_amount": entry.taxable_amount,
			"grand_total": doc_details.get("grand_total", 0),
			"base_total": doc_details.get("base_total", 0),
			"tax_amount": entry.withholding_amount,
			"transaction_date": entry.withholding_date,
			"transaction_type": entry.taxable_doctype,
			"ref_no": entry.taxable_name,
			"taxable_date": entry.taxable_date,
			"supplier_invoice_no": doc_details.get("bill_no"),
			"supplier_invoice_date": doc_details.get("bill_date"),
			"withholding_doctype": entry.withholding_doctype,
			"withholding_name": entry.withholding_name,
			"party_name": party_info.get("party_name"),
			"tax_id": entry.tax_id,
			"party": entry.party,
			"party_type": entry.party_type,
		}
		data.append(row)

	# Sort by section code and transaction date
	data.sort(key=lambda x: (x["section_code"] or "", x["transaction_date"] or ""))
	return data


def get_party_details(entries):
	"""Fetch party details in batch for all entries"""
	party_map = frappe._dict()
	parties_by_type = {"Customer": set(), "Supplier": set()}

	# Group parties by type
	for entry in entries:
		if entry.party_type in parties_by_type and entry.party:
			parties_by_type[entry.party_type].add(entry.party)

	# Batch fetch for each party type
	for party_type, party_set in parties_by_type.items():
		if not party_type or not party_set:
			continue

		doctype = frappe.qb.DocType(party_type)
		fields = [doctype.name]

		if party_type == "Supplier":
			fields.extend([doctype.supplier_type.as_("entity_type"), doctype.supplier_name.as_("party_name")])
		elif party_type == "Customer":
			fields.extend([doctype.customer_type.as_("entity_type"), doctype.customer_name.as_("party_name")])

		query = frappe.qb.from_(doctype).select(*fields).where(doctype.name.isin(party_set))
		party_details = query.run(as_dict=True)

		for party in party_details:
			party_map[(party_type, party.name)] = party

	return party_map


def get_columns(filters):
	"""Generate report columns based on filters"""
	columns = [
		{
			"label": _("Section Code"),
			"options": "Tax Withholding Category",
			"fieldname": "section_code",
			"fieldtype": "Link",
			"width": 90,
		},
		{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 60},
		{
			"label": _(f"{filters.get('party_type', 'Party')} Name"),
			"fieldname": "party_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _(filters.get("party_type", "Party")),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 180,
		},
		{
			"label": _("Entity Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Supplier Invoice No"),
			"fieldname": "supplier_invoice_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Supplier Invoice Date"),
			"fieldname": "supplier_invoice_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Tax Rate %"),
			"fieldname": "rate",
			"fieldtype": "Percent",
			"width": 60,
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Base Total"),
			"fieldname": "base_total",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Tax Amount"),
			"fieldname": "tax_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Reference Date"),
			"fieldname": "taxable_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Transaction Type"),
			"fieldname": "transaction_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Reference No."),
			"fieldname": "ref_no",
			"fieldtype": "Dynamic Link",
			"options": "transaction_type",
			"width": 180,
		},
		{
			"label": _("Date of Transaction"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Withholding Document"),
			"fieldname": "withholding_name",
			"fieldtype": "Dynamic Link",
			"options": "withholding_doctype",
			"width": 150,
		},
	]

	return columns


def get_tax_withholding_entries(filters):
	twe = frappe.qb.DocType("Tax Withholding Entry")
	query = (
		frappe.qb.from_(twe)
		.select(
			twe.company,
			twe.party_type,
			twe.party,
			IfNull(twe.tax_id, "").as_("tax_id"),
			twe.tax_withholding_category,
			IfNull(twe.tax_withholding_group, "").as_("tax_withholding_group"),
			twe.taxable_amount,
			twe.tax_rate,
			twe.withholding_amount,
			IfNull(twe.taxable_doctype, "").as_("taxable_doctype"),
			IfNull(twe.taxable_name, "").as_("taxable_name"),
			twe.taxable_date,
			IfNull(twe.under_withheld_reason, "").as_("under_withheld_reason"),
			IfNull(twe.lower_deduction_certificate, "").as_("lower_deduction_certificate"),
			IfNull(twe.withholding_doctype, "").as_("withholding_doctype"),
			IfNull(twe.withholding_name, "").as_("withholding_name"),
			twe.withholding_date,
			twe.status,
		)
		.where(twe.docstatus == 1)
		.where(twe.withholding_date >= filters.from_date)
		.where(twe.withholding_date <= filters.to_date)
		.where(IfNull(twe.withholding_name, "") != "")
		.where(twe.status != "Duplicate")
	)

	if filters.get("company"):
		query = query.where(twe.company == filters.get("company"))

	if filters.get("party_type"):
		query = query.where(twe.party_type == filters.get("party_type"))

	if filters.get("party"):
		query = query.where(twe.party == filters.get("party"))

	return query.run(as_dict=True)


def get_additional_doc_info(entries):
	"""Fetch additional document information in batch"""
	doc_info = {}
	docs_by_type = {
		"Purchase Invoice": set(),
		"Sales Invoice": set(),
		"Payment Entry": set(),
		"Journal Entry": set(),
	}

	# Group documents by type
	for entry in entries:
		if entry.taxable_name and entry.taxable_doctype in docs_by_type:
			docs_by_type[entry.taxable_doctype].add(entry.taxable_name)

	for doctype_name, voucher_set in docs_by_type.items():
		if voucher_set:
			_fetch_doc_info(doctype_name, voucher_set, doc_info)

	return doc_info


def _fetch_doc_info(doctype_name, voucher_set, doc_info):
	doctype = frappe.qb.DocType(doctype_name)
	fields = [doctype.name]

	# Add doctype-specific fields
	if doctype_name == "Purchase Invoice":
		fields.extend([doctype.grand_total, doctype.base_total, doctype.bill_no, doctype.bill_date])
	elif doctype_name == "Sales Invoice":
		fields.extend([doctype.grand_total, doctype.base_total])
	elif doctype_name == "Payment Entry":
		fields.extend(
			[doctype.paid_amount_after_tax.as_("grand_total"), doctype.base_paid_amount.as_("base_total")]
		)
	elif doctype_name == "Journal Entry":
		fields.extend([doctype.total_debit.as_("grand_total"), doctype.total_debit.as_("base_total")])
	else:
		return

	query = frappe.qb.from_(doctype).select(*fields).where(doctype.name.isin(voucher_set))
	entries = query.run(as_dict=True)

	for entry in entries:
		doc_info[(doctype_name, entry.name)] = entry
