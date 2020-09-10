# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments

def execute(filters=None):
	if not filters:
		return [], []
	
	validate_filters(filters)

	columns = get_columns(filters)

	data = get_data(filters)

	return columns, data

def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))
	
	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date"))))
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if (filters.get("pos_profile") and filters.get("group_by") == _('Group by POS Profile')):
		frappe.throw(_("Can not filter based on POS Profile, if grouped by POS Profile"))
	
	if (filters.get("customer") and filters.get("group_by") == _('Group by Customer')):
		frappe.throw(_("Can not filter based on Customer, if grouped by Customer"))
	
	if (filters.get("cashier") and filters.get("group_by") == _('Group by Cashier')):
		frappe.throw(_("Can not filter based on Cashier, if grouped by Cashier"))
	
	if (filters.get("mode_of_payment") and filters.get("group_by") == _('Group by Payment Method')):
		frappe.throw(_("Can not filter based on Payment Method, if grouped by Payment Method"))


def get_data(filters):
	conditions = get_conditions(filters)
	
	group_by_field = get_group_by_field(filters.get("group_by"))
	order_by = "posting_date"
	if group_by_field:
		order_by += ", {}".format(group_by_field)

	pos_entries = frappe.db.sql(
		"""
		SELECT 
			p.posting_date, p.name as pos_invoice, p.pos_profile,
			p.owner as cashier, p.base_grand_total as grand_total,
			p.customer, p.is_return
		FROM
			`tabPOS Invoice` p
		WHERE
			{conditions}
		ORDER BY
			{order_by}
		""".format(conditions=conditions, order_by=order_by), filters, as_dict=1)
	
	if filters.get("group_by") != "Group by Payment Method":
		mode_of_payments = get_mode_of_payments(set([d.pos_invoice for d in pos_entries]))

		for entry in pos_entries:
			if mode_of_payments.get(entry.pos_invoice):
				entry.mode_of_payment = ", ".join(mode_of_payments.get(entry.pos_invoice, []))

	return pos_entries

def get_conditions(filters):
	conditions = "company = %(company)s AND posting_date >= %(from_date)s AND posting_date <= %(to_date)s".format(
		company=filters.get("company"),
		from_date=filters.get("from_date"),
		to_date=filters.get("to_date"))

	if filters.get("pos_profile"):
		conditions += " AND pos_profile = %(pos_profile)s".format(pos_profile=filters.get("pos_profile"))
	
	if filters.get("cashier"):
		conditions += " AND owner = %(cashier)s".format(cashier=filters.get("cashier"))
	
	if filters.get("customer"):
		conditions += " AND customer = %(customer)s".format(customer=filters.get("customer"))
	
	if filters.get("mode_of_payment"):
		conditions += """
			AND EXISTS(
					SELECT name FROM `tabSales Invoice Payment` sip
					WHERE parent=p.name AND ifnull(sip.mode_of_payment, '') = %(mode_of_payment)s
				)"""
	
	if filters.get("is_return"):
		conditions += " AND is_return = %(is_return)s".format(is_return=filters.get("is_return"))
	
	return conditions

def get_group_by_field(group_by):
	group_by_field = ""

	if group_by == "Group by POS Profile":
		group_by_field = "pos_profile"
	elif group_by == "Group by Cashier":
		group_by_field = "owner"
	elif group_by == "Group by Customer":
		group_by_field = "customer"
	
	return group_by_field

def get_columns(filters):
	columns = [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label": _("POS Invoice"),
			"fieldname": "pos_invoice",
			"fieldtype": "Link",
			"options": "POS Invoice",
			"width": 120
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},
		{
			"label": _("POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 160
		},
		{
			"label": _("Cashier"),
			"fieldname": "cashier",
			"fieldtype": "Link",
			"options": "User",
			"width": 140
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 140
		},
		{
			"label": _("Payment Method"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 160
		},
		{
			"label": _("Is Return"),
			"fieldname": "is_return",
			"fieldtype": "Data",
			"width": 80
		},
	]

	return columns