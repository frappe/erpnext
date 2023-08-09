# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	validate_filters(filters)
	(
		tds_docs,
		tds_accounts,
		tax_category_map,
		journal_entry_party_map,
		net_total_map,
	) = get_tds_docs(filters)

	columns = get_columns(filters)

	res = get_result(
		filters, tds_docs, tds_accounts, tax_category_map, journal_entry_party_map, net_total_map
	)
	return columns, res


def validate_filters(filters):
	"""Validate if dates are properly set"""
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))


def get_result(
	filters, tds_docs, tds_accounts, tax_category_map, journal_entry_party_map, net_total_map
):
	party_map = get_party_pan_map(filters.get("party_type"))
	tax_rate_map = get_tax_rate_map(filters)
	gle_map = get_gle_map(tds_docs)

	out = []
	for name, details in gle_map.items():
		tax_amount, total_amount, grand_total, base_total = 0, 0, 0, 0
		tax_withholding_category = tax_category_map.get(name)
		rate = tax_rate_map.get(tax_withholding_category)

		for entry in details:
			party = entry.party or entry.against
			posting_date = entry.posting_date
			voucher_type = entry.voucher_type

			if voucher_type == "Journal Entry":
				party_list = journal_entry_party_map.get(name)
				if party_list:
					party = party_list[0]

			if not tax_withholding_category:
				tax_withholding_category = party_map.get(party, {}).get("tax_withholding_category")
				rate = tax_rate_map.get(tax_withholding_category)

			if entry.account in tds_accounts:
				tax_amount += entry.credit - entry.debit

			if net_total_map.get(name):
				total_amount, grand_total, base_total = net_total_map.get(name)
			else:
				total_amount += entry.credit

		if tax_amount:
			if party_map.get(party, {}).get("party_type") == "Supplier":
				party_name = "supplier_name"
				party_type = "supplier_type"
				table_name = "Supplier"
			else:
				party_name = "customer_name"
				party_type = "customer_type"
				table_name = "Customer"

			row = {
				"pan"
				if frappe.db.has_column(table_name, "pan")
				else "tax_id": party_map.get(party, {}).get("pan"),
				"party": party_map.get(party, {}).get("name"),
			}

			if filters.naming_series == "Naming Series":
				row.update({"party_name": party_map.get(party, {}).get(party_name)})

			row.update(
				{
					"section_code": tax_withholding_category,
					"entity_type": party_map.get(party, {}).get(party_type),
					"rate": rate,
					"total_amount": total_amount,
					"grand_total": grand_total,
					"base_total": base_total,
					"tax_amount": tax_amount,
					"transaction_date": posting_date,
					"transaction_type": voucher_type,
					"ref_no": name,
				}
			)
			out.append(row)

	return out


def get_party_pan_map(party_type):
	party_map = frappe._dict()

	fields = ["name", "tax_withholding_category"]
	if party_type == "Supplier":
		fields += ["supplier_type", "supplier_name"]
	else:
		fields += ["customer_type", "customer_name"]

	if frappe.db.has_column(party_type, "pan"):
		fields.append("pan")

	party_details = frappe.db.get_all(party_type, fields=fields)

	for party in party_details:
		party.party_type = party_type
		party_map[party.name] = party

	return party_map


def get_gle_map(documents):
	# create gle_map of the form
	# {"purchase_invoice": list of dict of all gle created for this invoice}
	gle_map = {}

	gle = frappe.db.get_all(
		"GL Entry",
		{"voucher_no": ["in", documents], "is_cancelled": 0},
		["credit", "debit", "account", "voucher_no", "posting_date", "voucher_type", "against", "party"],
	)

	for d in gle:
		if not d.voucher_no in gle_map:
			gle_map[d.voucher_no] = [d]
		else:
			gle_map[d.voucher_no].append(d)

	return gle_map


def get_columns(filters):
	pan = "pan" if frappe.db.has_column("Supplier", "pan") else "tax_id"
	columns = [
		{"label": _(frappe.unscrub(pan)), "fieldname": pan, "fieldtype": "Data", "width": 60},
		{
			"label": _(filters.get("party_type")),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 180,
		},
	]

	if filters.naming_series == "Naming Series":
		columns.append(
			{"label": _("Party Name"), "fieldname": "party_name", "fieldtype": "Data", "width": 180}
		)

	columns.extend(
		[
			{
				"label": _("Date of Transaction"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 100,
			},
			{
				"label": _("Section Code"),
				"options": "Tax Withholding Category",
				"fieldname": "section_code",
				"fieldtype": "Link",
				"width": 90,
			},
			{"label": _("Entity Type"), "fieldname": "entity_type", "fieldtype": "Data", "width": 100},
			{
				"label": _("Total Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Float",
				"width": 90,
			},
			{
				"label": _("TDS Rate %") if filters.get("party_type") == "Supplier" else _("TCS Rate %"),
				"fieldname": "rate",
				"fieldtype": "Percent",
				"width": 90,
			},
			{
				"label": _("Tax Amount"),
				"fieldname": "tax_amount",
				"fieldtype": "Float",
				"width": 90,
			},
			{
				"label": _("Grand Total"),
				"fieldname": "grand_total",
				"fieldtype": "Float",
				"width": 90,
			},
			{
				"label": _("Base Total"),
				"fieldname": "base_total",
				"fieldtype": "Float",
				"width": 90,
			},
			{"label": _("Transaction Type"), "fieldname": "transaction_type", "width": 100},
			{
				"label": _("Reference No."),
				"fieldname": "ref_no",
				"fieldtype": "Dynamic Link",
				"options": "transaction_type",
				"width": 180,
			},
		]
	)

	return columns


def get_tds_docs(filters):
	tds_documents = []
	purchase_invoices = []
	sales_invoices = []
	payment_entries = []
	journal_entries = []
	tax_category_map = frappe._dict()
	net_total_map = frappe._dict()
	or_filters = frappe._dict()
	journal_entry_party_map = frappe._dict()
	bank_accounts = frappe.get_all("Account", {"is_group": 0, "account_type": "Bank"}, pluck="name")

	tds_accounts = frappe.get_all(
		"Tax Withholding Account", {"company": filters.get("company")}, pluck="account"
	)

	query_filters = {
		"account": ("in", tds_accounts),
		"posting_date": ("between", [filters.get("from_date"), filters.get("to_date")]),
		"is_cancelled": 0,
		"against": ("not in", bank_accounts),
	}

	party = frappe.get_all(filters.get("party_type"), pluck="name")
	query_filters.update({"against": ("in", party)})

	if filters.get("party"):
		del query_filters["account"]
		del query_filters["against"]
		or_filters = {"against": filters.get("party"), "party": filters.get("party")}

	tds_docs = frappe.get_all(
		"GL Entry",
		filters=query_filters,
		or_filters=or_filters,
		fields=["voucher_no", "voucher_type", "against", "party"],
	)

	for d in tds_docs:
		if d.voucher_type == "Purchase Invoice":
			purchase_invoices.append(d.voucher_no)
		if d.voucher_type == "Sales Invoice":
			sales_invoices.append(d.voucher_no)
		elif d.voucher_type == "Payment Entry":
			payment_entries.append(d.voucher_no)
		elif d.voucher_type == "Journal Entry":
			journal_entries.append(d.voucher_no)

		tds_documents.append(d.voucher_no)

	if purchase_invoices:
		get_doc_info(purchase_invoices, "Purchase Invoice", tax_category_map, net_total_map)

	if sales_invoices:
		get_doc_info(sales_invoices, "Sales Invoice", tax_category_map, net_total_map)

	if payment_entries:
		get_doc_info(payment_entries, "Payment Entry", tax_category_map, net_total_map)

	if journal_entries:
		journal_entry_party_map = get_journal_entry_party_map(journal_entries)
		get_doc_info(journal_entries, "Journal Entry", tax_category_map)

	return (
		tds_documents,
		tds_accounts,
		tax_category_map,
		journal_entry_party_map,
		net_total_map,
	)


def get_journal_entry_party_map(journal_entries):
	journal_entry_party_map = {}
	for d in frappe.db.get_all(
		"Journal Entry Account",
		{"parent": ("in", journal_entries), "party_type": "Supplier", "party": ("is", "set")},
		["parent", "party"],
	):
		if d.parent not in journal_entry_party_map:
			journal_entry_party_map[d.parent] = []
		journal_entry_party_map[d.parent].append(d.party)

	return journal_entry_party_map


def get_doc_info(vouchers, doctype, tax_category_map, net_total_map=None):
	if doctype == "Purchase Invoice":
		fields = [
			"name",
			"tax_withholding_category",
			"base_tax_withholding_net_total",
			"grand_total",
			"base_total",
		]
	elif doctype == "Sales Invoice":
		fields = ["name", "base_net_total", "grand_total", "base_total"]
	elif doctype == "Payment Entry":
		fields = [
			"name",
			"tax_withholding_category",
			"paid_amount",
			"paid_amount_after_tax",
			"base_paid_amount",
		]
	else:
		fields = ["name", "tax_withholding_category"]

	entries = frappe.get_all(doctype, filters={"name": ("in", vouchers)}, fields=fields)

	for entry in entries:
		tax_category_map.update({entry.name: entry.tax_withholding_category})
		if doctype == "Purchase Invoice":
			net_total_map.update(
				{entry.name: [entry.base_tax_withholding_net_total, entry.grand_total, entry.base_total]}
			)
		elif doctype == "Sales Invoice":
			net_total_map.update({entry.name: [entry.base_net_total, entry.grand_total, entry.base_total]})
		elif doctype == "Payment Entry":
			net_total_map.update(
				{entry.name: [entry.paid_amount, entry.paid_amount_after_tax, entry.base_paid_amount]}
			)


def get_tax_rate_map(filters):
	rate_map = frappe.get_all(
		"Tax Withholding Rate",
		filters={
			"from_date": ("<=", filters.get("from_date")),
			"to_date": (">=", filters.get("to_date")),
		},
		fields=["parent", "tax_withholding_rate"],
		as_list=1,
	)

	return frappe._dict(rate_map)
