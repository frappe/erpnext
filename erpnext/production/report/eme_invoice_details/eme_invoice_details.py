# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_data(filters):
	query = frappe.db.sql("""
	SELECT 
			ep.branch,  
			ep.supplier, 
			ep.from_date, 
			ep.to_date, 
			epi.equipment_type, 
			epi.equipment, 
			SUM(IFNULL(epi.total_hours,0)) as total_hours, 
			epi.rate, 
			SUM(IFNULL(epi.amount,0)) as amount, 
			(SELECT e.supplier FROM `tabEquipment` e WHERE e.name= epi.equipment) AS owner_name, 
			(SELECT e.bank FROM `tabEquipment` e WHERE e.name= epi.equipment) AS bank_name, 
			(SELECT e.account_number FROM `tabEquipment` e WHERE e.name= epi.equipment) AS account_number 
			FROM `tabEME Invoice` ep, `tabEME Invoice Item` epi  
			WHERE epi.parent = ep.name AND ep.name = '{name}' 
			GROUP BY  epi.equipment_no
		""".format(name=filters.get("name"),as_dict=True))
	return query

def get_columns():
	return [
		{
			"fieldname":"branch",
			"label":_("Branch"),
			"fieldtype":"Link",
			"options":"Branch",
			"width":120
		},
		{
			"fieldname":"supplier",
			"label":_("Supplier"),
			"fieldtype":"Link",
			"options":"Supplier",
			"width":120
		},
		{
			"fieldname":"from_date",
			"label":_("From date"),
			"fieldtype":"Date",
			"width":120
		},
		{
			"fieldname":"to_date",
			"label":_("To date"),
			"fieldtype":"Date",
			"width":120
		},
		{
			"fieldname":"equipment_type",
			"label":_("Equipment Type"),
			"fieldtype":"Link",
			"options":"Equipment Type",
			"width":120
		},
		{
			"fieldname":"equipment",
			"label":_("Equipment"),
			"fieldtype":"Link",
			"options":"Equipment",
			"width":120
		},
		{
			"fieldname":"total_hours",
			"label":_("Total Hours"),
			"fieldtype":"Float",
			"width":120
		},
		{
			"fieldname":"rate",
			"label":_("Rate"),
			"fieldtype":"Currency",
			"width":120
		},
		{
			"fieldname":"amount",
			"label":_("Amount"),
			"fieldtype":"Currency",
			"width":120
		},
		{
			"fieldname":"owner_name",
			"label":_("Owner Name"),
			"fieldtype":"Data",
			"width":120
		},
		{
			"fieldname":"bank_name",
			"label":_("Bank Name"),
			"fieldtype":"Link",
			"options":"Financial Institution",
			"width":120
		},
		{
			"fieldname":"account_number",
			"label":_("Account Number"),
			"fieldtype":"Data",
			"width":120
		}
	]