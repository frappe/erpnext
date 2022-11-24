# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt, getdate, add_days, formatdate
from frappe import msgprint, _, qb, throw, bold
from calendar import monthrange
from erpnext.accounts.report.financial_statements import (
	get_daily_period_list
)

def execute(filters=None):
	period_list = get_daily_period_list(filters.from_date, filters.to_date)
	columns = get_columns(filters, period_list)
	data = get_data(filters, period_list)
	return columns, data

def get_data(filters, period_list):
	data = []
	exp_map = get_eme_expenses()
	total_actual_hours 		= frappe._dict({"expense_head":"Total, Actual Hours"})
	# assin 0 value for all columns total sum of hours
	for p in period_list:
		total_actual_hours[str(p.key)] = 0

	scheduled_wh = ["<b>Scheduled Hour</b>"]
	for exp in exp_map:
		hr_row 		= frappe._dict({"reading":"Hours"})
		fr 			= frappe._dict({"reading":"FR"})
		ir 			= frappe._dict({"reading":"IR"})
		tar 		= frappe._dict({"reading":"Target Trip"})
		ach 		= frappe._dict({"reading":"Achieved Trip"})
		trip_hour 	= frappe._dict({"reading":"Trip Hours"})
		total_hr 	= frappe._dict({"reading":"Total Hours"})
		flg = False
		for p in period_list:
			res = frappe.db.sql("""SELECT MAX(l.scheduled_working_hour) AS swh, 
											SUM(li.hours) AS hours, li.uom,
											li.target_trip, MIN(li.initial_reading) AS ir, 
											MIN(li.reading_initial) AS hir, 
											MAX(li.final_reading) AS fr, 
											MAX(li.reading_final) AS hfr 
									FROM `tabLogbook Item` li, tabLogbook l WHERE l.name = li.parent 
									AND l.docstatus = 1 AND l.posting_date = %(posting_date)s 
									AND li.expense_head = %(expense_head)s 
									AND l.equipment = %(eqp)s 
									GROUP BY li.uom""", {"posting_date": p.key, "expense_head": exp.name, "eqp": filters.equipment}, as_dict=1)
			total_hour = 0
			if res:
				flg = True
				for a in res:
					if a.uom == "Hour":	
						hr_row[str(p.key)] 	= flt(a.hours,2)
						fr[str(p.key)]     	= flt(a.hfr,2)
						ir[str(p.key)]		= flt(a.hir,2)
						tar[str(p.key)]  	= 0
						ach[str(p.key)]		= 0
						trip_hour[str(p.key)] = 0
					else:
						#keep default
						hr_row[str(p.key)] 	= 0
						fr[str(p.key)]     	= 0
						ir[str(p.key)]		= 0
						tar[str(p.key)]  	= flt(a.target_trip,2)
						ach[str(p.key)]		= flt(a.ir,2)
						trip_hour[str(p.key)] = flt(a.hours,2)
					total_hour =  flt(total_hour) + flt(a.hours)
				total_hr[str(p.key)] = flt(total_hour,2)
				total_actual_hours[str(p.key)] += flt(total_hour,2)
			else:
				hr_row[str(p.key)] 	= 0
				fr[str(p.key)]     	= 0
				ir[str(p.key)]		= 0
				tar[str(p.key)]  	= 0
				ach[str(p.key)]		= 0
				trip_hour[str(p.key)] = 0
				total_hr[str(p.key)] = 0
		if flg:
			data.append(frappe._dict({"expense_head":exp.name	}))
			data.append(hr_row)
			data.append(fr)
			data.append(ir)
			data.append(tar)
			data.append(ach)
			data.append(trip_hour)
			data.append(total_hr)
	data.append([])
	data.append(total_actual_hours)
	data.append([])
	data.append(frappe._dict({"expense_head":"Performance Record"}))
	return data

def get_columns(filters, period_list):
	columns = []
	columns.append({"fieldname":"expense_head",
					"fieldtype":"Data",
					"label":"Expense Head",
					"width":150})
	columns.append({"fieldname":"reading",
					"fieldtype":"Data",
					"label":"Reading",
					"width":120})
	for p in period_list:
		columns.append({
			"fieldname":str(p.key),
			"label":p.label,
			"fieldtype":"Float"
		})
	return columns

def get_eme_expenses():
	exp_head = qb.DocType("Expense Head")
	return (qb.from_(exp_head).select(exp_head.name).where(exp_head.disabled==0).orderby(exp_head.order_index)).run(as_dict=1)

def get_per_ava():
	query = "select name, type as reason_type from `tabDowntime Reason` order by type"
	return frappe.db.sql(query, as_dict=1)


