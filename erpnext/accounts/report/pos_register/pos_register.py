# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

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
	conditions = get_conditions(filters)
	order_by = "p.posting_date"
	select_mop_field, from_sales_invoice_payment, group_by_mop_condition = "", "", ""
	if group_by_field == "mode_of_payment":
		select_mop_field = ", sip.mode_of_payment, sip.base_amount - IF(sip.type='Cash', p.change_amount, 0) as paid_amount"
		from_sales_invoice_payment = ", `tabSales Invoice Payment` sip"
		group_by_mop_condition = "sip.parent = p.name AND ifnull(sip.base_amount - IF(sip.type='Cash', p.change_amount, 0), 0) != 0 AND"
		order_by += ", sip.mode_of_payment"

	elif group_by_field:
		order_by += ", p.{}".format(group_by_field)
		select_mop_field = ", p.base_paid_amount - p.change_amount  as paid_amount "

	return frappe.db.sql(
		"""
		SELECT
			p.posting_date, p.name as pos_invoice, p.pos_profile,
			p.owner, p.customer, p.is_return, p.base_grand_total as grand_total {select_mop_field}
		FROM
			`tabPOS Invoice` p {from_sales_invoice_payment}
		WHERE
			p.docstatus = 1 and
			{group_by_mop_condition}
			{conditions}
		ORDER BY
			{order_by}
		""".format(
			select_mop_field=select_mop_field,
			from_sales_invoice_payment=from_sales_invoice_payment,
			group_by_mop_condition=group_by_mop_condition,
			conditions=conditions,
			order_by=order_by,
		),
		filters,
		as_dict=1,
	)


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


def get_conditions(filters):
	conditions = (
		"company = %(company)s AND posting_date >= %(from_date)s AND posting_date <= %(to_date)s"
	)

	if filters.get("pos_profile"):
		conditions += " AND pos_profile = %(pos_profile)s"

	if filters.get("owner"):
		conditions += " AND owner = %(owner)s"

	if filters.get("customer"):
		conditions += " AND customer = %(customer)s"

	if filters.get("is_return"):
		conditions += " AND is_return = %(is_return)s"

	if filters.get("mode_of_payment"):
		conditions += """
			AND EXISTS(
					SELECT name FROM `tabSales Invoice Payment` sip
					WHERE parent=p.name AND ifnull(sip.mode_of_payment, '') = %(mode_of_payment)s
				)"""

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
			"label": _("POS Invoice"),
			"fieldname": "pos_invoice",
			"fieldtype": "Link",
			"options": "POS Invoice",
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
			"options": "company:currency",
			"width": 120,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 120,
		},
		{
			"label": _("Payment Method"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 150,
		},
		{"label": _("Is Return"), "fieldname": "is_return", "fieldtype": "Data", "width": 80},
	]

	return columns
