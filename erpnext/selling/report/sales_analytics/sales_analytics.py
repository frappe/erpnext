# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate,flt
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):

	columns = get_columns(filters)

	data = gen_data(filters)

	chart = get_chart_data(columns)

	return columns, data ,None, chart

def get_columns(filters):

	columns =[
		{
			"label": _(filters["tree_type"]),
			"options": filters["tree_type"],
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _(filters["tree_type"] + " Name"),
			"fieldname": "code",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Float",
			"width": 120
		}]

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for dummy, end_date in ranges:

		label = field_name = get_period(end_date,filters["range"])

		columns.append(
			{
			"label": _(label),
			"fieldname":field_name,
			"fieldtype": "Float",
			"width": 120
		},
		)

	return columns

def get_customer_by_group(filters):
	condition = ""

	if filters["tree_type"] == "Territory":
		condition = 'territory'

	if filters["tree_type"] == "Customer Group":
		condition = 'customer_group'

	return frappe.db.sql("""select c.name, c.customer_name as type_name, c.{condition} as grp , g.lft, g.rgt
		from `tabCustomer` c ,`tab{tree_type}` g
		where c.{condition} = g.name"""
		.format(tree_type=filters["tree_type"],condition=condition), as_dict=1)

def get_item_by_group():

	return frappe.db.sql("""select i.name, i.item_name as type_name, i.item_group as grp, i.stock_uom, g.lft , g.rgt from `tabItem` i,`tabItem Group` g
		where i.item_group = g.name """,as_dict=1)

def get_customer():
	return frappe.get_list("Customer", fields=["name","customer_name as type_name"])

def get_items(filters):
	return frappe.get_list("Item", fields=["name","item_name as type_name"], filters={"company":filters["company"]})

def get_period(date,duration):

	months ={"1":"Jan","2":"Feb","3":"Mar","4":"Apr","5":"May","6":"Jun","7":"Jul","8":"Aug",
		"9":"Sep","10":"Oct","11":"Nov","12":"Dec"}

	if duration == 'Weekly':
		period = "Week"+str(date.isocalendar()[1])
	elif duration == 'Monthly':
		period = months.get(str(date.month))
	elif duration == 'Quarterly':
		period = "Quarter" + str(((date.month-1)//3)+1)
	else:
		year = get_fiscal_year(date)
		period = str(year[2])

	return period

def get_data_list(entry,filters):
	data_list = {}
	for d in entry:
		date_field = filters["doc_type"] in ['Sales Order','Purchase Order'] and d.transaction_date or d.posting_date
		period = get_period(date_field,filters["range"])

		if data_list.get(d.name) :
			if data_list.get(d.name).get(period):
				data_list[d.name][period] += flt(d.select_field,2)
			else:
				data_list[d.name][period] = flt(d.select_field,2)
		else:
			data_list.setdefault(d.name,{}).setdefault(period,flt(d.select_field,2))

	return data_list

def get_customer_entry(filters):

	date_field = filters["doc_type"] in ['Sales Order', 'Purchase Order'] and 'transaction_date' or 'posting_date'

	if filters["value_quantity"] == 'Value':
		select = "base_net_total as select_field"
	else:
		select = "total_qty as select_field"

	entry = frappe.get_all(filters["doc_type"],
		fields=["customer as name",select, date_field],
		filters={
			"docstatus": 1,
			"company": filters["company"],
			date_field: ('between', [filters["from_date"],filters["to_date"]])
		}
	)

	return entry

def get_item_entry(filters):

	date_field = filters["doc_type"] in ['Sales Order', 'Purchase Order'] and 'transaction_date' or 'posting_date'

	if filters["value_quantity"] == 'Value':
		select = 'base_amount'
	else:
		select = 'qty'

	entry = frappe.db.sql("""
		select i.item_code as name, i.{select} as select_field,s.{date_field} 
		from `tab{doctype} Item` i ,`tab{doctype}` s
		where s.name = i.parent and i.docstatus = 1 and s.company = %s
		and s.{date_field} between %s and %s
	"""
	.format(date_field=date_field,select = select,doctype=filters["doc_type"]),
	(filters["company"], filters["from_date"], filters["to_date"]), as_dict=1)

	return entry

def get_type_data(filters,entry,type_list):
	data=[]

	data_list = get_data_list(entry,filters)

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for d in type_list:
		row = {}
		total = 0
		row["name"] = d.name
		row["code"] = d.type_name
		for dummy, end_date in ranges:
			period = get_period(end_date, filters["range"])

			if data_list.get(d.type_name) and data_list.get(d.type_name).get(period) :
				row[period] = data_list.get(d.type_name).get(period)
			else:
				row[period] = 0.0
			total += row[period]
		row["total"] = total
		data.append(row)

	return data

def get_by_group(filters,type_list,entry):
	data = []

	data_list = get_data_list(entry,filters)

	groups,depth_map = get_groups(filters)

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for g in groups:
		out = []
		g_total = 0

		group = {
			"name":g.name,
			"indent":depth_map.get(g.name),
			"code":g.name
		}

		for d in type_list:
			total = 0
			if d.lft >= g.lft and d.rgt <= g.rgt :
				row = {
					"name":d.name,
					"code":d.type_name,
					"indent":depth_map.get(g.name) + 1 
				}

				for dummy, end_date in ranges:
					period = get_period(end_date, filters["range"])
					if data_list.get(d.name) and data_list.get(d.name).get(period) :
						row[period] = data_list.get(d.name).get(period)
					else:
						row[period] = 0.0
					total += row[period]
					if group.get(period):
						group[period] += row[period]
					else:
						group[period] = row[period]
				row["total"] = total
				g_total += total
				if d.grp == g.name:
					out.append(row)

		group["total"] = g_total
		data.append(group)
		data += out

	return data

def get_groups(filters):

	if filters["tree_type"] == "Territory":
		parent = 'parent_territory'
	if filters["tree_type"] == "Customer Group":
		parent = 'parent_customer_group'
	if filters["tree_type"] == "Item Group":
		parent = 'parent_item_group'
	if filters["tree_type"] == "Supplier Group":
		parent = 'parent_supplier_group'

	depth_map = {}

	entry = frappe.db.sql("""select name, lft, rgt , {parent} as parent from `tab{tree}` order by lft""" 
	.format(tree=filters["tree_type"],parent=parent), as_dict=1)

	for d in entry:
		if d.parent:
			depth_map.setdefault(d.name,depth_map.get(d.parent) + 1)
		else:
			depth_map.setdefault(d.name,0)

	return entry,depth_map

def get_chart_data(columns):

	labels = [d.get("label") for d in columns[3:]]
	chart = {
		"data": {
			'labels': labels,
			'datasets':[
				{ "values": ['0' for d in columns[3:]] }
			]
		}
	}

	chart["type"] = "line"

	return chart

def get_period_date_ranges(period, fiscal_year=None, year_start_date=None, year_end_date=None):
	from dateutil.relativedelta import relativedelta

	if not (year_start_date and year_end_date) :
		year_start_date, year_end_date = frappe.db.get_value("Fiscal Year",
			fiscal_year, ["year_start_date", "year_end_date"])

	increment = {
		"Monthly": 1,
		"Quarterly": 3,
		"Half-Yearly": 6,
		"Yearly": 12
	}.get(period)

	period_date_ranges = []
	if period == 'Weekly':
		for dummy in range(1,53):
			period_end_date = getdate(year_start_date) + relativedelta(days=6)
			period_date_ranges.append([year_start_date, period_end_date])
			year_start_date = getdate(period_end_date) + relativedelta(days=1)
	else:
		for dummy in range(1, 13, increment):
			period_end_date = getdate(year_start_date) + relativedelta(months=increment, days=-1)
			if period_end_date > getdate(year_end_date):
				period_end_date = year_end_date
			period_date_ranges.append([year_start_date, period_end_date])
			year_start_date = getdate(period_end_date) + relativedelta(days=1)
			if period_end_date == year_end_date:
				break

	return period_date_ranges

def gen_data(filters):

	if filters["tree_type"] == 'Customer':

		entry = get_customer_entry(filters)

		customers = get_customer()

		return get_type_data(filters,entry,customers)

	elif filters["tree_type"] == 'Item':

		entry = get_item_entry(filters)

		items = get_items(filters)

		return get_type_data(filters,entry,items)

	elif filters["tree_type"] == 'Territory' or filters["tree_type"] == 'Customer Group' :
		customer = get_customer_by_group(filters)
		entry = get_customer_entry(filters)
		return get_by_group(filters,customer,entry)

	elif filters["tree_type"] == 'Item Group' :
		items = get_item_by_group()
		entry = get_item_entry(filters)
		return get_by_group(filters,items,entry)










