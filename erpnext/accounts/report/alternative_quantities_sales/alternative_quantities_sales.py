# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, date_diff
from frappe import _

def execute(filters=None):
	
	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, filters)
	validate_filters(filters)

	return columns,data
	
def get_columns(filters):
	columns = []

	lst =[ 
		{
			"fieldname": "item_code",
			"label": "Item Code",
			"width": 200,
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "item_name",
			"label": "Item Name",
			"width": 200,
			"fieldtype": "Data"
		},
		{
			"fieldname": "brand",
			"label": "Brand",
			"width": 150,
			"fieldtype": "Data"
		},
		{
			"fieldname": "qty",
			"label": "Alternate Qty",
			"width": 100,
			"fieldtype": "Float"
		},
		{
			"fieldname": "amount",
			"label": "Total",
			"width": 100,
			"fieldtype": "Float"
		},
		{
			"fieldname": "rate",
			"label": " Avg Price",
			"width": 100,
			"fieldtype": "Float"
		},

	]

	columns.extend(lst)
	return columns

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")
	group, based = filters.get("group_by"), filters.get("based_on")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

def get_data(conditions, filters):
	query = frappe.db.sql(
		""" 
		Select 
		sii.item_code as item_code,
		sii.item_name as item_name,
		i.brand,
		sii.qty,
		sii.rate,
		sii.amount
		
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si ON si.name = sii.parent
		join `tabItem` i ON  i.item_code = sii.item_code
		join `tabSales Team` st On st.parent = si.name
		where si.docstatus = 1
		{conditions}
		""".format(conditions=conditions),filters, as_dict=1
	)
	return query

def get_conditions(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " AND si.posting_date between %(from_date)s and %(to_date)s"

	if filters.get("company"):
		conditions += " AND si.company = %(company)s"

	if filters.get("warehouse"):
		conditions += " AND sii.warehouse = %(warehouse)s"

	if filters.get("item_group"):
		conditions += " AND i.item_group = %(item_group)s"

	if filters.get("item_category"):
		conditions += " AND i.item_category = %(item_category)s"		

	if filters.get("territory"):
		conditions += " AND si.territory = %(territory)s"	

	if filters.get("costcenter"):
		conditions += " AND sii.cost_center = %(costcenter)s"

	if filters.get("customer"):
		conditions += " AND si.customer = %(customer)s"	

	if filters.get("sales_person"):
		conditions += " AND st.sales_person = %(sales_person)s"						
	return conditions