# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.query_builder import DocType
from frappe import qb,_


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	if filters.aggregate:
		cols = [
			("Equipment/Vehicle") + ":Link/Equipment:120",
			("Equipment Type")+":Link/Equipment Type:150",
			("Item")+":Link/Item:100",
			("Item Name")+":Data:130",
			("Rate")+":Currency:100",
			("Qty") +":Data:80",
			("Amount") +":Currency:100",
		]
	else:
		cols = [
			("Branch") + ":Link/Branch:200",
			("Posting Date") + ":Date:120",
			("Equipment/Vehicle") + ":Link/Equipment:120",
			("Equipment Type")+":Link/Equipment Type:130",
			("Current KM")+":Data:100",
			("KM Difference") + ":Data:100",
			("Item")+":Link/Item:100",
			("Item Name")+":Data:100",
			("Rate")+":Currency:100",
			("Qty") +":Float:80",
			("Amount") +":Currency:100",
			("Last Service Date") +":Date:100",
			("Repair & Services Type") + ":Data:130"
		]
	return cols

def get_data(filters):
	conditions = get_condition(filters)
	query = ''
	if filters.aggregate:
		query = '''
			SELECT 
				rs.equipment, rs.equipment_type,
				rsi.item_code, rsi.item_name,
				ROUND(SUM(rsi.rate * rsi.qty)/ SUM(rsi.qty),2), SUM(rsi.qty), SUM(rsi.charge_amount)
			FROM `tabRepair And Services` rs 
			INNER JOIN `tabRepair And Services Item` rsi ON rs.name = rsi.parent
			WHERE rs.docstatus = 1
			{}
			GROUP BY rs.equipment, rsi.item_code
		'''.format(conditions)
	else:
		query = '''
			SELECT rs.branch, rs.posting_date,
				rs.equipment, rs.equipment_type,
				rs.current_km, rs.km_difference,
				rsi.item_code, rsi.item_name,
				rsi.rate, rsi.qty, rsi.charge_amount,
				rsi.last_service_date, rs.repair_and_services_type
			FROM `tabRepair And Services` rs 
			INNER JOIN `tabRepair And Services Item` rsi ON rs.name = rsi.parent
			WHERE rs.docstatus = 1
			{}
		'''.format(conditions)
	return frappe.db.sql(query)

def get_condition(filters):
	conditions = ""
	if filters.get("branch"):
		conditions += " and rs.branch = '{}'".format(filters.branch)

	if filters.get("equipment"):
		conditions += " and rs.equipment ='{}' ".format(filters.equipment)

	if filters.get("equipment_type"):
		conditions += " and rs.equipment_type = '{}'".format(filters.equipment_type)
	
	if filters.from_date > filters.to_date:
		frappe.throw("From Date cannot be greater than To Date")

	if filters.from_date and filters.to_date:
		conditions += " and rs.posting_date between '{}' and '{}' ".format(filters.from_date, filters.to_date)

	if filters.repair_and_services_type:
		conditions += " and rs.repair_and_services_type = '{}'".format(filters.repair_and_services_type)
	return conditions