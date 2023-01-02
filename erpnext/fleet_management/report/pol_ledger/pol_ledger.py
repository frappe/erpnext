# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr, get_datetime
from erpnext.fleet_management.fleet_utils import get_pol_till, get_pol_till,get_pol_consumed_till
from operator import itemgetter, attrgetter
import datetime

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	data = []
	query = "select * from `tabPOL Entry` where docstatus = 1 "
	
	if filters.from_date and filters.to_date:
		query += " and posting_date between \'" + str(filters.from_date) + "\' and \'" + str(filters.to_date) + "\'"
	
	if filters.branch:
		query += " and branch = \'" + str(filters.branch) + "\'"

	if filters.equipment:
		query += " and equipment = \'" + str(filters.equipment) + "\'"

	query += " order by posting_date"
	# get_pol_till(purpose, equipment, date, pol_type=None)
	for eq in frappe.db.sql(query, as_dict=True):
		item = frappe.db.sql("select item_code, item_name, stock_uom from tabItem where `name`= \'" + str(eq.pol_type) + "\'", as_dict=True)
	
		branch = frappe.db.get_value(eq.reference_type, eq.reference_name, "branch")
		dc = "No"
		if eq.reference_type == "POL Recieve":
			pol = frappe.get_doc(eq.reference_type, eq.reference)
			if pol.direct_consumption:
				dc = "Yes"
	
#		get_pol_till(purpose, equipment, posting_date, pol_type=None, own_cc=None, posting_time="24:00"):
		received = get_pol_till("Receive", eq.equipment, eq.posting_date, eq.pol_type, posting_time=eq.posting_time )
		equipment = frappe.db.sql("select e.name, e.branch, e.equipment_type as equipment_type, et.is_container as is_container from tabEquipment e, `tabEquipment Type` et where e.equipment_type = et.name and e.name = \'" + str(eq.equipment) + "\'", as_dict=True)	
		if equipment[0]['is_container'] == 1:
			stock = get_pol_till("Stock", eq.equipment, eq.posting_date, eq.pol_type, posting_time=eq.posting_time)
			issued = get_pol_till("Issue", eq.equipment, eq.posting_date, eq.pol_type, posting_time=eq.posting_time)
			balance = flt(stock) - flt(issued)
		else:
			balance = 0
		if eq.type == "Issue":
			trans_qty = -eq.qty
		else:
			trans_qty = eq.qty

		row = frappe._dict({
			"posting_date":get_datetime(str(eq.posting_date) + " " + str(eq.posting_time)), 
			"branch":eq.branch, 
			"equipment":eq.equipment, 
			"item_name":item[0]['item_name'], 
			"trans_qty":trans_qty, 
			"balance":balance, 
			"type":eq.type, 
			"reference_type":eq.reference_type,
			"reference" :eq.reference, 
			"direct_comsumption": dc})
		data.append(row)
		
	return data

def get_columns():
	return [
		{"fieldname":"posting_date","fieldtype":"Datetime","width":150,"label":"Posting Date"},
		{"fieldname":"branch","fieldtype":"Link","width":130,"label":"Branch", "options":"Branch"},
		{"fieldname":"equipment","fieldtype":"Link","width":120,"label":"Equipment", "options":"Equipment"},
		{"fieldname":"item_name","fieldtype":"Data","width":100,"label":"Item Name"},
		{"fieldname":"trans_qty","fieldtype":"Float","width":100,"label":"Qty"},
		{"fieldname":"balance","fieldtype":"Float","width":100,"label":"Tanker Balance"},
		{"fieldname":"type","fieldtype":"Data","width":100,"label":"Type"},
		{"fieldname":"reference_type","fieldtype":"Data","width":100,"label":"Reference Type"},
		{"fieldname":"reference","fieldtype":"Data","width":100,"label":"Reference"},
		{"fieldname":"direct_comsumption","fieldtype":"Data","width":100,"label":"Is Direct Consumption"},
	]
