# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_data(filters):
	return frappe.db.sql("""
					SELECT 
						ep.branch,
						epi.posting_date,
						ep.from_date,
						ep.to_date, 
						ep.supplier,
						ep.name as ref,
						ep.tds_percent,
						ep.tds_amount,
						ep.total_amount,
						ep.deduction_amount,
						ep.payable_amount,
						epi.rate,
						epi.equipment_type,
						ep.remarks,
						(SELECT count(DISTINCT equipment) 
								FROM `tabEME Invoice Item` 
								WHERE parent = '{name}' 
								and rate = epi.rate   
								and equipment_type = epi.equipment_type) AS no,
						(SELECT SUM(total_hours) 
								FROM `tabEME Invoice Item` 
								WHERE parent = '{name}'
								and rate = epi.rate 
								and equipment_type = epi.equipment_type) AS total_hours 
					FROM `tabEME Invoice` ep, `tabEME Invoice Item` epi
					WHERE ep.name = epi.parent
					and ep.name = "{name}"
					group by epi.rate
			""".format(name=filters.name), as_dict=True)

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
			"fieldname":"posting_date",
			"label":_("Posting Date"),
			"fieldtype":"Date",
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
			"fieldname":"no",
			"label":_("Nos"),
			"fieldtype":"Float",
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
		}
	]