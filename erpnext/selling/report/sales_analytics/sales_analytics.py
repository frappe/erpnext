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

	return frappe.db.sql("""select c.name, c.customer_name, c.{condition}, g.lft, g.rgt
		from `tabCustomer` c ,`tab{tree_type}` g
		where c.{condition} = g.name"""
		.format(tree_type=filters["tree_type"],condition=condition), as_dict=1)

def get_item_by_group():

	return frappe.db.sql("""select i.name, i.item_name, i.item_group, i.stock_uom, g.lft , g.rgt from `tabItem` i,`tabItem Group` g
		where i.item_group = g.name """,as_dict=1)

def get_customer():
	return frappe.get_list("Customer", fields=["name","customer_name"])

def get_items():
	return frappe.get_list("Item", fields=["name","item_name"])

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

def get_customer_data(filters):
	data=[]
	date_field = filters["doc_type"] == 'Sales Order' and 'transaction_date' or 'posting_date'

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

	data_list = get_data_list(entry,filters)

	if filters["tree_type"] == 'Territory' or filters["tree_type"] == 'Customer Group':
		return data_list

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for d in get_customer():
		customer = {}
		total = 0
		customer["name"] = d.name
		customer["code"] = d.customer_name
		for dummy, end_date in ranges:
			period = get_period(end_date, filters["range"])

			if data_list.get(d.name) and data_list.get(d.name).get(period) :
				customer[period] = data_list.get(d.name).get(period)
			else:
				customer[period] = 0.0
			total += customer[period]
		customer["total"] = total
		data.append(customer)

	return data

def get_item_data(filters):
	data=[]

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
			.format(date_field=date_field,select = select,
			doctype=filters["doc_type"]),
			(filters["company"], filters["from_date"], filters["to_date"]), as_dict=1)


	data_list = get_data_list(entry,filters)

	if filters["tree_type"] == 'Item Group':
		return data_list

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for d in get_items():
		item = {}
		total = 0
		item["name"] = d.item_name
		item["code"] = d.name
		for dummy, end_date in ranges:
			period = get_period(end_date, filters["range"])
			if data_list.get(d.name) and data_list.get(d.name).get(period) :
				item[period] = data_list.get(d.name).get(period)
			else:
				item[period] = 0.0
			total += item[period]
		item["total"] = total
		data.append(item)

	return data

def get_by_group(filters):
	data = []

	depth_map = get_groups(filters)

	data_list = get_customer_data(filters)

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])
	cust = get_customer_by_group(filters)

	previous_lft = 0
	previous_rgt = 10000000000
	indent = -1

	for g in depth_map:
		out = []

		if g.lft > previous_lft and g.rgt < previous_rgt:
			indent += 1
		else:
			indent -= 1

		group = {
			"name":g.name,
			"indent":indent,
			"code":g.name
		}
		g_total = 0
		for d in cust:
			if d.lft >= g.left and d.rgt <= g.rgt :
				condition = d.territory if filters["tree_type"] == "Territory" else d.customer_group
				customer = {
					"name":d.name,
					"code":d.customer_name,
					"indent":indent+1
				}
				total = 0

				for dummy, end_date in ranges:
					period = get_period(end_date, filters["range"])
					if data_list.get(d.name) and data_list.get(d.name).get(period) :
						customer[period] = data_list.get(d.name).get(period)
					else:
						customer[period] = 0.0
					total += customer[period]
					if group.get(period):
						group[period] += customer[period]
					else:
						group[period] = customer[period]
				customer["total"] = total
				g_total += total
				if condition == g.name:
					out.append(customer)
		group["total"] = g_total
		data.append(group)
		data += out
		previous_lft = g.lft
		previous_rgt = g.rgt

	return data


def get_groups(filters):

	entry = frappe.db.sql("""select name, lft, rgt from `tab{tree}` order by lft""" .format(tree=filters["tree_type"]), as_dict=1)

	return entry

def get_by_item_group(filters):
	data = []

	depth_map = get_groups(filters)

	data_list = get_item_data(filters)

	items = get_item_by_group()

	previous_lft = 0
	previous_rgt = 10000000000
	indent = -1 

	for g in depth_map:

		if g.lft > previous_lft and g.rgt < previous_rgt:
			indent += 1
		else:
			indent -= 1

		group = {
			"name":g.name,
			"indent":indent,
			"code":g.name
		}
		g_total= 0
		out = []

		ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

		for d in items:
			if d.lft >= g.lft and d.rgt <= g.rgt :
				item = {
					"name":d.name,
					"code":d.item_name,
					"indent":indent + 1
				}
				total = 0

				for dummy, end_date in ranges:
					period = get_period(end_date, filters["range"])
					if data_list.get(d.name) and data_list.get(d.name).get(period) :
						item[period] = data_list.get(d.name).get(period)
					else:
						item[period] = 0.0
					total += item[period]
					if group.get(period):
						group[period] += item[period]
					else:
						group[period] = item[period]
				item["total"] = total
				g_total += total
				if d.item_group == g.name:
					out.append(item)
		group["total"] = g_total
		data.append(group)
		data += out
		previous_lft = g.lft
		previous_rgt = g.rgt

	return data

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
		return get_customer_data(filters)

	elif filters["tree_type"] == 'Item':
		return get_item_data(filters)

	elif filters["tree_type"] == 'Territory' or filters["tree_type"] == 'Customer Group' :
		return get_by_group(filters)

	elif filters["tree_type"] == 'Item Group' :
		return get_by_item_group(filters)










