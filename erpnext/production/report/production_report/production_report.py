# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.accounts_custom_functions import get_child_cost_centers
from frappe.utils import flt
from frappe import _, qb, throw

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	data = []
	conditions = get_conditions(filters)
	group_by = get_group_by(filters)
	order_by = get_order_by(filters)
	total_qty = '1'
	if filters.show_aggregate:
		total_qty = "sum(pe.qty) as total_qty"
	query = """
	select	
		pe.ref_doc,
		pe.posting_date, 
		pe.item_code, 
		pe.item_name, 
		pe.item_group, 
		pe.item_sub_group, 
		pe.qty, 
		pe.uom, 
		pe.equipment_number, 
		pe.equipment_model, 
		pe.transporter_type, 
		pe.unloading_by, 
		pe.mineral_raising_group,
		pe.coal_raising_type, 
		pe.branch, 
		pe.location, 
		pe.adhoc_production, 
		pe.company, 
		pe.warehouse,
		pe.transfer_to_warehouse,
		pe.transportation_rate,
		pe.transportation_amount,
		cc.parent_cost_center as region,
		{0} 
	from 
		`tabProduction Entry` pe, 
		`tabCost Center` cc
	where 
		pe.docstatus = 1 
	
	and 
		cc.name = pe.cost_center {1} {2} {3}""".format(total_qty, conditions, group_by, order_by)
	abbr = " - " + str(frappe.db.get_value("Company", filters.company, "abbr"))

	total_qty = 0

	for a in frappe.db.sql(query, as_dict=1):
		if filters.show_aggregate:
			a.qty = a.total_qty
		total_qty += flt(a.qty)
		data.append(a)
	data.append({"qty": total_qty, "branch": frappe.bold("TOTAL")})
	return data

def get_group_by(filters):
	if filters.show_aggregate:
		group_by = " group by pe.branch, pe.location, pe.item_code "
	else:
		group_by = ""

	return group_by

def get_order_by(filters):
	return " order by region, pe.location, pe.item_group, pe.item_code"

def get_conditions(filters):
	condition = ''
	all_ccs = get_child_cost_centers(filters.cost_center)
	if len(all_ccs) > 1:
		all_branch = []
		for a in all_ccs:
			all_branch.append(str(a))
		if all_branch:
			condition += " and pe.cost_center in {0} ".format(tuple(all_branch))
	elif filters.cost_center:
		condition += " and pe.cost_center = '{0}' ".format(filters.cost_center)

	if filters.production_type != "All":
		condition += " and pe.production_type = '{0}'".format(filters.production_type)

	if filters.location:
		condition += " and pe.location = '{0}'".format(filters.location)

	if filters.adhoc_production:
		condition += " and pe.adhoc_production = '{0}'".format(filters.adhoc_production)

	if filters.item_group:
		condition += " and pe.item_group = '{0}'".format(filters.item_group)

	if filters.item:
		condition += " and pe.item_code = '{0}'".format(filters.item)

	if filters.get("from_date") and filters.get("to_date"):
		condition += " and DATE(pe.posting_date) between '{0}' and '{1}'".format(filters.from_date, filters.to_date)

	if filters.warehouse:
		condition += " and pe.warehouse = '{0}'".format(filters.warehouse)

	if filters.branch:
		condition += " and pe.branch = '{}' ".format(filters.branch)
	return condition

def get_columns(filters):
	columns = [
		{
			"fieldname": "branch",
			"label": "Branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 120
		},
		{
			"fieldname": "location",
			"label": "Location",
			"fieldtype": "Link",
			"options": "Location",
			"width": 120
		},
		{
			"fieldname": "item_group",
			"label": "Item Group",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "item_code",
			"label": "Material Code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "qty",
			"label": "Quantity",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "handling_loss",
			"label": "Handling Loss",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "uom",
			"label": "UOM",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100
		},
		{
			"fieldname": "handling_loss",
			"label": "Handling Loss",
			"fieldtype": "Float",
			"width": 100
		},
	]

	if not filters.show_aggregate:
		columns.insert(0,{
			"fieldname": "ref_doc",
			"label": "Reference",
			"fieldtype": "Link",
			"options": "Production",
			"width": 150
		}),
		columns.insert(3, {
			"fieldname": "transfer_to_warehouse",
			"label": "Transfer to Warehouse",
			"fieldtype": "Data",
			"width": 150
			})
		columns.insert(5, {
			"fieldname": "posting_date",
			"label": "Posting Date",
			"fieldtype": "Date",
			"width": 100
		})
		columns.insert(9, {
			"fieldname": "transportation_rate",
			"label": "Transportation rate",
			"fieldtype": "Currency",
			"width": 120
			})
		columns.insert(10, {
			"fieldname": "transportation_amount",
			"label": "Transportation Amount",
			"fieldtype": "Currency",
			"width": 150
			})
		columns.insert(11, {
	        "fieldname": "equipment_number",	                        
			"label": "Equipment Number",
            "fieldtype": "Data",														                      "width": 130									                
			})
		columns.insert(12, {
			"fieldname": "equipment_model",
			"label": "Equipment Model",
			"fieldtype": "Data",
			"width": 130 
			})
		columns.insert(13, {
			"fieldname": "transporter_type",
			"label": "Transporter Type",
			"fieldtype": "Data",
			"width": 130
			})
		columns.insert(14, {
			"fieldname": "unloading_by",
			"label": "Unloading By",
			"fieldtype": "Data",
			"width": 120
			})
		columns.insert(15, {
			"fieldname": "mineral_raising_group",
			"label": "Mineral Raising Group",
			"fieldtype": "Link",
			"options":"Mineral Raising Group",
			"width": 120
			})
		columns.insert(16, {
			"fieldname": "coal_raising_type",
			"label": "Coal Raising Type",
			"fieldtype": "Data",
			"width": 120
			})
	return columns

