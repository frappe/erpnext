# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, date_diff
from frappe import _

def execute(filters=None):
	
	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, filters)
	report_summary = get_summary(conditions, filters)
	chart = get_chart_data(conditions, filters)
	
# 	report_summary = [
#     {"label":"cats","value":2287,'indicator':'Red'},
#     {"label":"dogs","value":3647,'indicator':'Blue'}
# ]
	
	validate_filters(filters)

	return columns, data, None, chart, report_summary
	
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
			"fieldname": "uom",
			"label": "UOM",
			"width": 100,
			"fieldtype": "Data"
		},
		{
			"fieldname": "qty",
			"label": "Qty",
			"width": 100,
			"fieldtype": "Float"
		},
		
		{
			"fieldname": "stock_uom",
			"label": "Stock UOM",
			"width": 100,
			"fieldtype": "Data"
		},
		{
			"fieldname": "stock_qty",
			"label": "Stock Qty",
			"width": 100,
			"fieldtype": "Float"
		},
			{
			"fieldname": "weight_uom",
			"label": "Weight UOM",
			"width": 100,
			"fieldtype": "Data"
		},
		{
			"fieldname": "total_weight",
			"label": "Total Weight",
			"width": 100,
			"fieldtype": "Float"
		},
		{
			"fieldname": "amount",
			"label": "Total",
			"width": 100,
			"fieldtype": "Currency"
		},
		{
			"fieldname": "rate",
			"label": " Avg Price",
			"width": 100,
			"fieldtype": "Currency"
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
		sum(sii.qty) qty,
		sii.uom,
		sii.stock_uom,
		sii.weight_uom,
		sum(sii.stock_qty) as stock_qty,
		sum(sii.total_weight) as total_weight,
		sii.base_rate as rate,
		sum(sii.amount) as amount
		
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si ON si.name = sii.parent
		join `tabItem` i ON  i.item_code = sii.item_code
		join `tabSales Team` st ON st.parent = si.name
		join `tabCustomer` c ON c.name = si.customer
		where si.docstatus = 1
		{conditions}
		Group BY sii.item_code
		""".format(conditions=conditions),filters, as_dict=1
	)
	return query

def get_summary(conditions, filters):

	query = frappe.db.sql(
		"""
		Select
 			round(sum(sii.total_weight)) as total_weight,
 			round(sum(sii.qty)) as qty

		from `tabSales Invoice Item` sii
				join `tabSales Invoice` si ON si.name = sii.parent
				join `tabItem` i ON  i.item_code = sii.item_code
				join `tabSales Team` st On st.parent = si.name
				join `tabCustomer` c ON c.name = si.customer
			
		where si.docstatus = 1
		{conditions}
		""".format(conditions=conditions),filters, as_dict=1
	)

	return [
		{"label":"","value": "",'indicator':'Red'},
		{"label":"Total Weight","value":query[0].total_weight,'indicator':'Red'},
		{"label":"","value": "",'indicator':'Blue'},
   		{"label":"Total Qty","value":query[0].qty,'indicator':'Blue'},
		{"label":"","value": "",'indicator':'Red'},
	]	

def get_chart_data(conditions, filters):
	
	group_by = filters.get("group_by")
	
	if group_by == "Customer Group":

		query = frappe.db.sql(
			"""
				Select

					c.customer_group,
					sum(sii.total_weight) as weight,
					sum(sii.qty)  as qty
					
					from `tabSales Invoice Item` sii
						join `tabSales Invoice` si ON si.name = sii.parent
						join `tabItem` i ON  i.item_code = sii.item_code
						join `tabSales Team` st On st.parent = si.name
						join `tabCustomer` c ON c.name = si.customer

					where si.docstatus = 1
					{conditions}
					Group by c.customer_group 
					Order by c.customer_group 
			""".format(conditions=conditions),filters, as_dict=1
		)

		labels = []
		value = []
		value2 =[]
		for q in query:
			labels.append(q.get("customer_group"))
			value.append(q.get("weight"))
			value2.append(q.get("qty"))
		datasets = []
		if value:
			datasets.append({'name': _('Total Weight'), 'values': value})

		if value2:
			datasets.append({'name': _('Total Qty'), 'values': value2})	
		chart = {
			"data": {
				'labels': labels,
				'datasets': datasets
			}
		}
		chart["type"] = "bar"
		return chart
	else:
		query = frappe.db.sql(
			"""
				Select

					monthname(si.posting_date) as month,
					sum(sii.total_weight) as weight,
					sum(sii.qty)  as qty
					

					from `tabSales Invoice Item` sii
						join `tabSales Invoice` si ON si.name = sii.parent
						join `tabItem` i ON  i.item_code = sii.item_code
						join `tabSales Team` st On st.parent = si.name
						join `tabCustomer` c ON c.name = si.customer
						where si.docstatus = 1					
					{conditions}

					Group by monthname(si.posting_date) 
					Order by  month(si.posting_date)
			""".format(conditions=conditions),filters, as_dict=1
		)

		labels = []
		value = []
		value2 =[]
		for q in query:
			labels.append(q.get("month"))
			value.append(q.get("weight"))
			value2.append(q.get("qty"))
		datasets = []
		if value:
			datasets.append({'name': _('Total Weight'), 'values': value})

		if value2:
			datasets.append({'name': _('Total Qty'), 'values': value2})	
		chart = {
			"data": {
				'labels': labels,
				'datasets': datasets
			}
		}
		chart["type"] = "bar"
		return chart


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

	if filters.get("customer_group"):
		conditions += " AND c.customer_group = %(customer_group)s"					
	return conditions