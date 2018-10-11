# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.selling.report.sales_analytics.sales_analytics import (get_columns, get_period,
	get_period_date_ranges, get_chart_data, get_item_by_group, get_data_list, get_item_data,get_depth_map,get_by_item_group)


def execute(filters=None):
	columns = get_columns(filters)

	data = gen_data(filters)

	chart = get_chart_data(filters,columns,data)

	return columns, data, None, chart

def get_supplier_by_group(filters):

	return frappe.db.sql("""select c.name, c.supplier_name, c.supplier_group, g.lft, g.rgt
							from `tabSupplier` c ,`tab{tree_type}` g
							where c.supplier_group = g.name"""
			.format(tree_type=filters["tree_type"]), as_dict=1)

def get_supplier():
	return frappe.get_list("Supplier", fields=["name","supplier_name"])

def get_supplier_data(filters):
	data=[]
	date_field = filters["doc_type"] == 'Purchase Order' and 'transaction_date' or 'posting_date'

	if filters["value_quantity"] == 'Value':
		select = "base_net_total as select_field"
	else:
		select = "total_qty as select_field"

	entry = frappe.get_all(filters["doc_type"],
		fields=["supplier as name",select, date_field],
		filters={
			"docstatus": 1,
			"company": filters["company"],
			date_field: ('between', [filters["from_date"],filters["to_date"]])
		}
	)

	data_list = get_data_list(entry,filters)

	if filters["tree_type"] == 'Supplier Group':
		return data_list

	ranges = get_period_date_ranges(filters["range"],year_start_date=filters["from_date"], year_end_date=filters["to_date"])

	for d in get_supplier():
		supplier = {}
		total = 0
		supplier["name"] = d.name
		supplier["code"] = d.supplier_name
		for dummy, end_date in ranges:
			period = get_period(end_date, filters["range"])

			if data_list.get(d.name) and data_list.get(d.name).get(period) :
				supplier[period] = data_list.get(d.name).get(period)
			else:
				supplier[period] = 0.0
			total += supplier[period]
		supplier["total"] = total
		data.append(supplier)

	return data

def get_by_group(filters):
	data = []

	group = frappe.db.sql("""select name,lft,rgt from `tab{tree}` where lft = 1  """.format(tree=filters["tree_type"]),as_dict=1)

	depth_map = get_depth_map(filters,group,0,[])

	data_list = get_supplier_data(filters)

	ranges = get_period_date_ranges(filters["range"],year_start_date=filters["from_date"], year_end_date=filters["to_date"])

	supp = get_supplier_by_group(filters)

	for g in depth_map:
		out = []
		group = {}
		g_total = 0
		group["name"] = g.get("name")
		group["indent"] = g.get("depth")
		group["code"] = g.get("name")
		for d in supp:
			if d.lft >= g.get("lft") and d.rgt <= g.get("rgt") :
				supplier = {}
				total = 0
				supplier["name"] = d.name
				supplier["code"] = d.supplier_name
				supplier["indent"] = g.get("depth")+1
				for dummy, end_date in ranges:
					period = get_period(end_date, filters["range"])
					if data_list.get(d.name) and data_list.get(d.name).get(period) :
						supplier[period] = data_list.get(d.name).get(period)
					else:
						supplier[period] = 0.0
					total += supplier[period]
					if group.get(period):
						group[period] += supplier[period]
					else:
						group[period] = supplier[period]
				supplier["total"] = total
				g_total += total
				if d.supplier_group== g.get("name"):
					out.append(supplier)
		group["total"] = g_total
		data.append(group)
		data += out

	return data


def gen_data(filters):

	if filters["tree_type"] == 'Supplier':
		return get_supplier_data(filters)
		
	elif filters["tree_type"] == 'Item':
		return get_item_data(filters)
	
	elif filters["tree_type"] == 'Supplier Group' :
		return get_by_group(filters)

	elif filters["tree_type"] == 'Item Group' :
		return get_by_item_group(filters)