# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint


def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	data = get_entries(filters)

	return columns, data

def get_columns(filters):
	if not filters.get("doctype"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns =[
		{
			"label": _("Sales Partner"),
			"options": "Sales Partner",
			"fieldname": "sales_partner",
			"fieldtype": "Link",
			"width": 100
		},
				{
			"label": _("Sales Partner Email"),
			"fieldname": "customer_primary_email_address",
			"fieldtype": "DATA",
			"width": 200
		},
		{
			"label": _("Sales Partner Rebate preference"),
			"fieldname": "bank_details",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _(filters["doctype"]),
			"options": filters["doctype"],
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 100
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 140
		},
		# {
		# 	"label": _("Territory"),
		# 	"options": "Territory",
		# 	"fieldname": "territory",
		# 	"fieldtype": "Link",
		# 	"width": 100
		# },
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100
		},
		# {
		# 	"label": _("Item Code"),
		# 	"fieldname": "item_code",
		# 	"fieldtype": "Link",
		# 	"options": "Item",
		# 	"width": 120
		# },
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 140
		},
		# {
		# 	"label": _("Item Group"),
		# 	"fieldname": "item_group",
		# 	"fieldtype": "Link",
		# 	"options": "Item Group",
		# 	"width": 100
		# },
		# {
		# 	"label": _("Brand"),
		# 	"fieldname": "brand",
		# 	"fieldtype": "Link",
		# 	"options": "Brand",
		# 	"width": 100
		# },
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},

		# {
		# 	"label": _("Commission Rate %"),
		# 	"fieldname": "commission_rate",
		# 	"fieldtype": "Data",
		# 	"width": 80
		# },
		{
			"label": _("Commission"),
			"fieldname": "commission",
			"fieldtype": "Currency",
			"width": 120
		}
		# {
		# 	"label": _("Currency"),
		# 	"fieldname": "currency",
		# 	"fieldtype": "Link",
		# 	"options": "Currency",
		# 	"width": 120
		# }
	]

	return columns

def get_entries(filters):
	date_field = ("transaction_date" if filters.get('doctype') == "Sales Order"
		else "posting_date")

	conditions = get_conditions(filters, date_field)
	entries = frappe.db.sql("""
		SELECT
			dt.name, dt.customer, dt.territory, dt.{date_field} as posting_date, dt.currency, 
			if(s.preference = "Refund to Account", s.bank_account, s.preference) as bank_details,
			dt_item.item_name, dt.customer_name,
			dt_item.base_net_rate as rate, dt_item.qty, dt_item.base_net_amount as amount,
			ROUND(((dt_item.base_net_amount * dt.commission_rate) / 100), 2) as commission,
			dt_item.brand, dt.sales_partner,dts.customer_primary_email_address, dt.commission_rate, dt_item.item_group, dt_item.item_code
		FROM
			`tab{doctype}` dt
		join `tab{doctype} Item` dt_item on dt_item.parent = dt.name
		join `tabSales Partner` s on s.name = dt.sales_partner
		join `tabCustomer` dts on dts.name = s.customer
		WHERE
			{cond} and dt.name = dt_item.parent 
			and dt.docstatus = 1
			and dt_item.item_code NOT IN ("HAND-FEE", "SHIP1", "SHIP2", "SHIP3")
			and dt.sales_partner is not null 
			and dt.sales_partner != ''
			order by dt.name desc, dt.sales_partner
		""".format(date_field=date_field, doctype=filters.get('doctype'),
			cond=conditions), filters, as_dict=1)

	return entries

def get_conditions(filters, date_field):
	conditions = "1=1"

	for field in ["company", "customer", "territory", "sales_partner"]:
		if filters.get(field):
			conditions += " and dt.{0} = %({1})s".format(field, field)

	if filters.get("from_date"):
		conditions += " and dt.{0} >= %(from_date)s".format(date_field)

	if filters.get("to_date"):
		conditions += " and dt.{0} <= %(to_date)s".format(date_field)

	if not filters.get('show_return_entries'):
		conditions += " and dt_item.qty > 0.0"

	if filters.get('brand'):
		conditions += " and dt_item.brand = %(brand)s"

	if filters.get('item_group'):
		lft, rgt = frappe.get_cached_value('Item Group',
			filters.get('item_group'), ['lft', 'rgt'])

		conditions += """ and dt_item.item_group in (select name from
			`tabItem Group` where lft >= %s and rgt <= %s)""" % (lft, rgt)


	return conditions
