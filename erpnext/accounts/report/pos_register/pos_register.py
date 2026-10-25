# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import IfNull
from frappe.utils import cstr

from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments


def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)

	columns = get_columns(filters)

	group_by_field = get_group_by_field(filters.get("group_by"))

	pos_entries = get_pos_entries(filters, group_by_field)
	if group_by_field != "mode_of_payment":
		concat_mode_of_payments(pos_entries)

	# return only entries if group by is unselected
	if not group_by_field:
		return columns, pos_entries

	# handle grouping
	invoice_map, grouped_data = {}, []
	for d in pos_entries:
		invoice_map.setdefault(d[group_by_field], []).append(d)

	for key in invoice_map:
		invoices = invoice_map[key]
		grouped_data += invoices
		add_subtotal_row(grouped_data, invoices, group_by_field, key)

	# move group by column to first position
	column_index = next(
		(index for (index, d) in enumerate(columns) if d["fieldname"] == group_by_field), None
	)
	columns.insert(0, columns.pop(column_index))

	return columns, grouped_data


def get_pos_entries(filters, group_by_field):
	"""POS sales from POS Invoices and from Sales Invoices made directly at the POS."""
	entries = get_invoice_entries("POS Invoice", filters, group_by_field)
	entries += get_invoice_entries("Sales Invoice", filters, group_by_field)
	sort_field = group_by_field or "posting_date"
	entries.sort(key=lambda d: (d.posting_date, cstr(d.get(sort_field))))
	if group_by_field == "mode_of_payment":
		show_grand_total_once(entries)
	return entries


def get_invoice_entries(doctype, filters, group_by_field):
	if not frappe.has_permission(doctype, "select"):
		return []

	p = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(p)
		.select(
			p.posting_date,
			ConstantColumn(doctype).as_("invoice_type"),
			p.name.as_("pos_invoice"),
			p.pos_profile,
			p.company,
			p.owner,
			p.customer,
			p.is_return,
			p.base_grand_total.as_("grand_total"),
		)
		.where(p.docstatus == 1)
		.where(p.name.isin(frappe.qb.get_query(doctype, fields=["name"], ignore_permissions=False)))
	)

	if doctype == "Sales Invoice":
		# consolidated invoices only merge POS Invoices that are already listed
		query = query.where((p.is_pos == 1) & (p.is_consolidated == 0))

	for condition in get_conditions(filters, p):
		query = query.where(condition)

	if group_by_field == "mode_of_payment":
		sip = frappe.qb.DocType("Sales Invoice Payment")
		paid_amount = sip.base_amount - Case().when(sip.type == "Cash", p.base_change_amount).else_(0)
		query = (
			query.inner_join(sip)
			.on((sip.parent == p.name) & (sip.parenttype == doctype))
			.select(sip.mode_of_payment, paid_amount.as_("paid_amount"))
			.where(IfNull(paid_amount, 0) != 0)
		)
	else:
		query = query.select((p.base_paid_amount - p.base_change_amount).as_("paid_amount"))

	return query.run(as_dict=1)


def show_grand_total_once(entries):
	"""An invoice has a row per payment; keep its grand total on the first so group totals add up."""
	seen = set()
	for entry in entries:
		invoice = (entry.invoice_type, entry.pos_invoice)
		if invoice in seen:
			entry.grand_total = 0
		seen.add(invoice)


def concat_mode_of_payments(pos_entries):
	mode_of_payments = get_mode_of_payments(set(d.pos_invoice for d in pos_entries))
	for entry in pos_entries:
		if mode_of_payments.get(entry.pos_invoice):
			entry.mode_of_payment = ", ".join(mode_of_payments.get(entry.pos_invoice, []))


def add_subtotal_row(data, group_invoices, group_by_field, group_by_value):
	grand_total = sum(d.grand_total for d in group_invoices)
	paid_amount = sum(d.paid_amount for d in group_invoices)
	data.append(
		{
			group_by_field: group_by_value,
			"grand_total": grand_total,
			"paid_amount": paid_amount,
			"bold": 1,
		}
	)
	data.append({})


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(
			_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date")))
		)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if filters.get("pos_profile") and filters.get("group_by") == _("POS Profile"):
		frappe.throw(_("Can not filter based on POS Profile, if grouped by POS Profile"))

	if filters.get("customer") and filters.get("group_by") == _("Customer"):
		frappe.throw(_("Can not filter based on Customer, if grouped by Customer"))

	if filters.get("owner") and filters.get("group_by") == _("Cashier"):
		frappe.throw(_("Can not filter based on Cashier, if grouped by Cashier"))

	if filters.get("mode_of_payment") and filters.get("group_by") == _("Payment Method"):
		frappe.throw(_("Can not filter based on Payment Method, if grouped by Payment Method"))


def get_conditions(filters, p):
	conditions = [
		p.company == filters.get("company"),
		p.posting_date >= filters.get("from_date"),
		p.posting_date <= filters.get("to_date"),
	]

	if filters.get("pos_profile"):
		conditions.append(p.pos_profile == filters.get("pos_profile"))

	if filters.get("owner"):
		conditions.append(p.owner == filters.get("owner"))

	if filters.get("customer"):
		conditions.append(p.customer == filters.get("customer"))

	if filters.get("is_return"):
		conditions.append(p.is_return == filters.get("is_return"))

	if filters.get("mode_of_payment"):
		sip = frappe.qb.DocType("Sales Invoice Payment")
		conditions.append(
			p.name.isin(
				frappe.qb.from_(sip)
				.select(sip.parent)
				.where(IfNull(sip.mode_of_payment, "") == filters.get("mode_of_payment"))
			)
		)

	return conditions


def get_group_by_field(group_by):
	group_by_field = ""

	if group_by == "POS Profile":
		group_by_field = "pos_profile"
	elif group_by == "Cashier":
		group_by_field = "owner"
	elif group_by == "Customer":
		group_by_field = "customer"
	elif group_by == "Payment Method":
		group_by_field = "mode_of_payment"

	return group_by_field


def get_columns(filters):
	columns = [
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 90},
		{
			"label": _("Invoice Type"),
			"fieldname": "invoice_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"label": _("Invoice"),
			"fieldname": "pos_invoice",
			"fieldtype": "Dynamic Link",
			"options": "invoice_type",
			"width": 120,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{
			"label": _("POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 160,
		},
		{
			"label": _("Cashier"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 120,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 120,
		},
		{
			"label": _("Payment Method"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 150,
		},
		{"label": _("Is Return"), "fieldname": "is_return", "fieldtype": "Data", "width": 80},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
	]

	return columns
