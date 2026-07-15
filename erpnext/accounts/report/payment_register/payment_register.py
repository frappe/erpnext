# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Coalesce

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	gle = qb.DocType("GL Entry")
	acc = qb.DocType("Account")
	pe = qb.DocType("Payment Entry")
	je = qb.DocType("Journal Entry")

	query = (
		qb.from_(gle)
		.inner_join(acc)
		.on(gle.account == acc.name)
		.left_join(pe)
		.on((gle.voucher_type == "Payment Entry") & (gle.voucher_no == pe.name))
		.left_join(je)
		.on((gle.voucher_type == "Journal Entry") & (gle.voucher_no == je.name))
		.select(
			gle.name,
			gle.posting_date,
			gle.company,
			gle.account,
			gle.account_currency,
			Coalesce(gle.party_type, pe.party_type).as_("party_type"),
			Coalesce(gle.party, pe.party).as_("party"),
			gle.debit,
			gle.credit,
			gle.debit_in_account_currency,
			gle.credit_in_account_currency,
			gle.against,
			gle.against_voucher_type,
			gle.against_voucher,
			gle.voucher_type,
			gle.voucher_no,
			gle.voucher_subtype,
			gle.cost_center,
			gle.project,
			gle.remarks,
			Coalesce(pe.mode_of_payment, je.mode_of_payment).as_("mode_of_payment"),
			Coalesce(pe.reference_no, je.cheque_no).as_("reference_no"),
			Coalesce(pe.reference_date, je.cheque_date).as_("reference_date"),
			Coalesce(pe.clearance_date, je.clearance_date).as_("clearance_date"),
		)
		.where(gle.is_cancelled == 0)
		.where(gle.is_opening == "No")
		.where(acc.account_type.isin(["Bank", "Cash"]))
	)

	query = apply_filters(query, filters, gle, pe, je)
	query = query.orderby(gle.posting_date).orderby(gle.name)

	data = query.run(as_dict=True)

	for row in data:
		if row.debit_in_account_currency:
			row.amount = row.debit_in_account_currency
			row.direction = _("Receive")
		else:
			row.amount = row.credit_in_account_currency
			row.direction = _("Pay")

		row.amount_in_company_currency = row.debit or row.credit

	return data


def apply_filters(query, filters, gle, pe, je):
	conditions = []

	if filters.company:
		conditions.append(gle.company == filters.company)

	if filters.from_date:
		conditions.append(gle.posting_date.gte(filters.from_date))

	if filters.to_date:
		conditions.append(gle.posting_date.lte(filters.to_date))

	if filters.party_type:
		conditions.append((gle.party_type == filters.party_type) | (pe.party_type == filters.party_type))

	if filters.party:
		parties = filters.party if isinstance(filters.party, list) else [filters.party]
		conditions.append((gle.party.isin(parties)) | (pe.party.isin(parties)))

	if filters.account:
		accounts = filters.account if isinstance(filters.account, list) else [filters.account]
		conditions.append(gle.account.isin(accounts))

	if filters.voucher_type:
		voucher_types = (
			filters.voucher_type if isinstance(filters.voucher_type, list) else [filters.voucher_type]
		)
		conditions.append(gle.voucher_type.isin(voucher_types))

	if filters.cost_center:
		conditions.append(gle.cost_center == filters.cost_center)

	if filters.mode_of_payment:
		conditions.append(Coalesce(pe.mode_of_payment, je.mode_of_payment) == filters.mode_of_payment)

	if filters.reference_no:
		conditions.append(
			(pe.reference_no.like(f"%{filters.reference_no}%"))
			| (je.cheque_no.like(f"%{filters.reference_no}%"))
		)

	for dimension in get_accounting_dimensions():
		if filters.get(dimension):
			conditions.append(gle[dimension] == filters.get(dimension))

	if conditions:
		query = query.where(Criterion.all(conditions))

	return query


def get_columns():
	return [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 160,
		},
		{
			"label": _("Voucher Subtype"),
			"fieldname": "voucher_subtype",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Direction"),
			"fieldname": "direction",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 100,
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 140,
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 160,
		},
		{
			"label": _("Against"),
			"fieldname": "against",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Against Voucher Type"),
			"fieldname": "against_voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"label": _("Against Voucher No"),
			"fieldname": "against_voucher",
			"fieldtype": "Dynamic Link",
			"options": "against_voucher_type",
			"width": 140,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120,
		},
		{
			"label": _("Currency"),
			"fieldname": "account_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"label": _("Amount (Company Currency)"),
			"fieldname": "amount_in_company_currency",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 150,
		},
		{
			"label": _("Mode of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Link",
			"options": "Mode of Payment",
			"width": 120,
		},
		{
			"label": _("Reference No"),
			"fieldname": "reference_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Reference Date"),
			"fieldname": "reference_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Clearance Date"),
			"fieldname": "clearance_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 120,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"fieldtype": "Data",
			"width": 200,
		},
	]
