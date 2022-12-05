# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

def execute(filters=None):
	columns, data = get_cols(filters), get_data(filters)
	return columns, data
def get_data(filters):
	cond = get_cond(filters)
	return frappe.db.sql('''
			SELECT e.branch, ei.equipment, ei.equipment_type, ei.operator,
				ei.operator_name, e.posting_date,
				e.name AS reference,ei.uom, ei.shift_type, ei.initial_km,
				ei.final_km, ei.total_km, date_format(ei.start_time, '%h:%i %p') AS start_time, 
				date_format(ei.end_time, '%h:%i %p') AS end_time, ei.total_hours, ei.trip_or_hole,
				CASE WHEN ei.trip_or_hole = 'Trip' THEN ei.no_of_trip ELSE ei.holes END as no_of_trip,
				ei.meterage_drilled,ei.qtymt, ei.ot_hr, ei.expense_head
			FROM `tabFleet Engagement` e
			INNER JOIN 
			`tabFleet Engagement Item` ei
			ON e.name = ei.parent 
			WHERE e.docstatus = 1
			{}
			'''.format(cond), as_dict=True)
	
def get_cond(filters):
	cond = ""
	if getdate(filters.form_date) > getdate(filters.to_date):
		frappe.throw("From Date cannot be greater than to date")
	if filters.from_date and filters.to_date:
		cond += " AND e.posting_date BETWEEN '{}' AND '{}' ".format(filters.from_date, filters.to_date)
	if filters.equipment:
		cond += " AND ei.equipment = '{}'".format(filters.equipment)
	if filters.branch:
		cond += " AND e.branch = '{}'".format(filters.branch)
	return cond
def get_cols(filters):
	return [
		{ "fieldname":"branch","fieldtype":"Link","options":"Branch","width":150,"label":"Branch"},
		{ "fieldname":"equipment","fieldtype":"Link","options":"Equipment","width":120,"label":"Vehicle/Equipment"},
		{ "fieldname":"equipment_type","fieldtype":"Link","options":"Equipment Type","width":120,"label":"Vehicle/Equipment Type"},
		{ "fieldname":"operator","fieldtype":"Link","options":"Employee","width":120,"label":"Operator"},
		{ "fieldname":"operator_name","fieldtype":"Data","width":120,"label":"Operator Name"},
		{ "fieldname":"posting_date","fieldtype":"Date","width":120,"label":"Posting Date"},
		{ "fieldname":"reference","fieldtype":"Link","options":"Fleet Engagement","width":120,"label":"Reference"},
		{ "fieldname":"shift_type","fieldtype":"Link","options":"Shift Type","width":80,"label":"Shift"},
		{ "fieldname":"uom","fieldtype":"Data","width":120,"label":"Reading UOM(KM/Hr)"},
		{ "fieldname":"initial_km","fieldtype":"Float","width":120,"label":"Initial KM/Hr"},
		{ "fieldname":"final_km","fieldtype":"Float","width":120,"label":"Final KM/Hr"},
		{ "fieldname":"total_km","fieldtype":"Float","width":120,"label":"Total KM"},
		{ "fieldname":"start_time","fieldtype":"Data","width":100,"label":"Start Time"},
		{ "fieldname":"end_time","fieldtype":"Data","width":100,"label":"End Time"},
		{ "fieldname":"total_hours","fieldtype":"Float","width":100,"label":"Total Hours"},
		{ "fieldname":"trip_or_hole","fieldtype":"Data","width":100,"label":"Reading UOM(Trip/Hole)"},
		{ "fieldname":"no_of_trip","fieldtype":"Float","width":100,"label":"No Of Trip/Hole"},
		{ "fieldname":"meterage_drilled","fieldtype":"Float","width":100,"label":"Meterage Drilled"},
		{ "fieldname":"qtymt","fieldtype":"Float","width":100,"label":"Qty(MT)"},
		{ "fieldname":"ot_hr","fieldtype":"Float","width":100,"label":"OT Hours"},
		{ "fieldname":"expense_head","fieldtype":"Link","options":"Expense Head","width":120,"label":"Nature Of Work"},
	]

