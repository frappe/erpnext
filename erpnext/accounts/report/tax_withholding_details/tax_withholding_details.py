# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnext.accounts.utils import get_currency_precision


def execute(filters=None):
	if filters.get("party_type") == "Customer":
		party_naming_by = frappe.get_single_value("Selling Settings", "cust_master_name")
	else:
		party_naming_by = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	filters["naming_series"] = party_naming_by

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
	filters = frappe._dict(filters or {})
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))


def get_result(filters, tds_docs, tds_accounts, tax_category_map, journal_entry_party_map, net_total_map):
	party_map = get_party_pan_map(filters.get("party_type"))
	tax_rate_map = get_tax_rate_map(filters)
	gle_map = get_gle_map(tds_docs)
	precision = get_currency_precision()

	out = []
	entries = {}
	for name, details in gle_map.items():
		for entry in details:
			tax_amount, total_amount, grand_total, base_total = 0, 0, 0, 0
			tax_withholding_category, rate = None, None
			bill_no, bill_date = "", ""
			party = entry.party or entry.against
			posting_date = entry.posting_date
			voucher_type = entry.voucher_type

			if voucher_type == "Journal Entry":
				party_list = journal_entry_party_map.get(name)
				if party_list:
					party = party_list[0]

			if entry.account in tds_accounts.keys():
				tax_amount += entry.credit - entry.debit
				# infer tax withholding category from the account if it's the single account for this category
				tax_withholding_category = tds_accounts.get(entry.account)
				# or else the consolidated value from the voucher document
				if not tax_withholding_category:
					tax_withholding_category = tax_category_map.get((voucher_type, name))
				# or else from the party default
				if not tax_withholding_category:
					tax_withholding_category = party_map.get(party, {}).get("tax_withholding_category")

				rate = get_tax_withholding_rates(tax_rate_map.get(tax_withholding_category, []), posting_date)

			values = net_total_map.get((voucher_type, name))

			if values:
				if voucher_type == "Journal Entry" and tax_amount and rate:
					# back calculate total amount from rate and tax_amount
					base_total = min(flt(tax_amount / (rate / 100), precision=precision), values[0])
					total_amount = grand_total = base_total

				else:
					if tax_amount and rate:
						# back calculate total amount from rate and tax_amount
						total_amount = flt((tax_amount * 100) / rate, precision=precision)
					else:
						total_amount = values[0]

					grand_total = values[1]
					base_total = values[2]

					if voucher_type == "Purchase Invoice":
						bill_no = values[3]
						bill_date = values[4]
			else:
				total_amount += entry.credit

			if tax_amount:
				if party_map.get(party, {}).get("party_type") == "Supplier":
					party_name = "supplier_name"
					party_type = "supplier_type"
				else:
					party_name = "customer_name"
					party_type = "customer_type"

				row = {
					"pan" if frappe.db.has_column(filters.party_type, "pan") else "tax_id": party_map.get(
						party, {}
					).get("pan"),
					"party": party_map.get(party, {}).get("name"),
				}

				if filters.naming_series == "Naming Series":
					row["party_name"] = party_map.get(party, {}).get(party_name)

				row.update(
					{
						"section_code": tax_withholding_category or "",
						"entity_type": party_map.get(party, {}).get(party_type),
						"rate": rate,
						"total_amount": total_amount,
						"grand_total": grand_total,
						"base_total": base_total,
						"tax_amount": tax_amount,
						"transaction_date": posting_date,
						"transaction_type": voucher_type,
						"ref_no": name,
						"supplier_invoice_no": bill_no,
						"supplier_invoice_date": bill_date,
					}
				)

				key = entry.voucher_no
				if key in entries:
					entries[key]["tax_amount"] += tax_amount
				else:
					entries[key] = row
	out = list(entries.values())
	out.sort(key=lambda x: (x["section_code"], x["transaction_date"]))

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
		if d.voucher_no not in gle_map:
			gle_map[d.voucher_no] = [d]
		else:
			gle_map[d.voucher_no].append(d)

	return gle_map


def get_columns(filters):
	pan = "pan" if frappe.db.has_column(filters.party_type, "pan") else "tax_id"
	columns = [
		{
			"label": _("Section Code"),
			"options": "Tax Withholding Category",
			"fieldname": "section_code",
			"fieldtype": "Link",
			"width": 90,
		},
		{"label": _(frappe.unscrub(pan)), "fieldname": pan, "fieldtype": "Data", "width": 60},
	]

	if filters.naming_series == "Naming Series":
		columns.append(
			{
				"label": _(filters.party_type + " Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 180,
			}
		)
	else:
		columns.append(
			{
				"label": _(filters.get("party_type")),
				"fieldname": "party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 180,
			}
		)

	columns.extend(
		[
			{"label": _("Entity Type"), "fieldname": "entity_type", "fieldtype": "Data", "width": 100},
		]
	)
	if filters.party_type == "Supplier":
		columns.extend(
			[
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
			]
		)

	columns.extend(
		[
			{
				"label": _("TDS Rate %") if filters.get("party_type") == "Supplier" else _("TCS Rate %"),
				"fieldname": "rate",
				"fieldtype": "Percent",
				"width": 60,
			},
			{
				"label": _("Total Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"label": _("Base Total"),
				"fieldname": "base_total",
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"label": _("TDS Amount") if filters.get("party_type") == "Supplier" else _("TCS Amount"),
				"fieldname": "tax_amount",
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"label": _("Grand Total"),
				"fieldname": "grand_total",
				"fieldtype": "Float",
				"width": 120,
			},
			{"label": _("Transaction Type"), "fieldname": "transaction_type", "width": 130},
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
	journal_entry_party_map = frappe._dict()
	bank_accounts = frappe.get_all("Account", {"is_group": 0, "account_type": "Bank"}, pluck="name")

	_tds_accounts = frappe.get_all(
		"Tax Withholding Account",
		{"company": filters.get("company")},
		["account", "parent"],
	)
	tds_accounts = {}
	for tds_acc in _tds_accounts:
		# if it turns out not to be the only tax withholding category, then don't include in the map
		if tds_acc["account"] in tds_accounts:
			tds_accounts[tds_acc["account"]] = None
		else:
			tds_accounts[tds_acc["account"]] = tds_acc["parent"]

	tds_docs = get_tds_docs_query(filters, bank_accounts, list(tds_accounts.keys())).run(as_dict=True)

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
		get_doc_info(journal_entries, "Journal Entry", tax_category_map, net_total_map)

	return (
		tds_documents,
		tds_accounts,
		tax_category_map,
		journal_entry_party_map,
		net_total_map,
	)


def get_tds_docs_query(filters, bank_accounts, tds_accounts):
	if not tds_accounts:
		frappe.throw(
			_("No {0} Accounts found for this company.").format(frappe.bold(_("Tax Withholding"))),
			title=_("Accounts Missing Error"),
		)
	gle = frappe.qb.DocType("GL Entry")
	query = (
		frappe.qb.from_(gle)
		.select("voucher_no", "voucher_type", "against", "party")
		.where(gle.is_cancelled == 0)
	)

	if filters.get("from_date"):
		query = query.where(gle.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		query = query.where(gle.posting_date <= filters.get("to_date"))

	if filters.get("party"):
		party = [filters.get("party")]
		jv_condition = gle.against.isin(party) | (
			(gle.voucher_type == "Journal Entry") & (gle.party == filters.get("party"))
		)
	else:
		party = frappe.get_all(filters.get("party_type"), pluck="name")
		jv_condition = gle.against.isin(party) | (
			(gle.voucher_type == "Journal Entry")
			& ((gle.party_type == filters.get("party_type")) | (gle.party_type == ""))
		)

	query.where((gle.account.isin(tds_accounts) & jv_condition) | gle.party.isin(party))
	if bank_accounts:
		query = query.where(
			gle.against.notin(bank_accounts) & (gle.account.isin(tds_accounts) & jv_condition)
			| gle.party.isin(party)
		)

	return query


def get_journal_entry_party_map(journal_entries):
	journal_entry_party_map = {}
	for d in frappe.db.get_all(
		"Journal Entry Account",
		{
			"parent": ("in", journal_entries),
			"party_type": ("in", ("Supplier", "Customer")),
			"party": ("is", "set"),
		},
		["parent", "party"],
	):
		if d.parent not in journal_entry_party_map:
			journal_entry_party_map[d.parent] = []
		journal_entry_party_map[d.parent].append(d.party)

	return journal_entry_party_map


def get_doc_info(vouchers, doctype, tax_category_map, net_total_map=None):
	common_fields = ["name"]
	fields_dict = {
		"Purchase Invoice": [
			"tax_withholding_category",
			"base_tax_withholding_net_total",
			"grand_total",
			"base_total",
			"bill_no",
			"bill_date",
		],
		"Sales Invoice": ["base_net_total", "grand_total", "base_total"],
		"Payment Entry": [
			"tax_withholding_category",
			"paid_amount",
			"paid_amount_after_tax",
			"base_paid_amount",
		],
		"Journal Entry": ["tax_withholding_category", "total_debit"],
	}

	entries = frappe.get_all(
		doctype, filters={"name": ("in", vouchers)}, fields=common_fields + fields_dict[doctype]
	)

	for entry in entries:
		tax_category_map[(doctype, entry.name)] = entry.tax_withholding_category
		if doctype == "Purchase Invoice":
			value = [
				entry.base_tax_withholding_net_total,
				entry.grand_total,
				entry.base_total,
				entry.bill_no,
				entry.bill_date,
			]
		elif doctype == "Sales Invoice":
			value = [entry.base_net_total, entry.grand_total, entry.base_total]
		elif doctype == "Payment Entry":
			value = [entry.paid_amount, entry.paid_amount_after_tax, entry.base_paid_amount]
		else:
			value = [entry.total_debit] * 3

		net_total_map[(doctype, entry.name)] = value


def get_tax_rate_map(filters):
	rate_map = frappe.get_all(
		"Tax Withholding Rate",
		filters={"from_date": ("<=", filters.to_date), "to_date": (">=", filters.from_date)},
		fields=["parent", "tax_withholding_rate", "from_date", "to_date"],
	)

	rate_list = frappe._dict()

	for rate in rate_map:
		rate_list.setdefault(rate.parent, []).append(frappe._dict(rate))

	return rate_list


def get_tax_withholding_rates(tax_withholding, posting_date):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding:
		if getdate(rate.from_date) <= getdate(posting_date) <= getdate(rate.to_date):
			return rate.tax_withholding_rate

	return 0
