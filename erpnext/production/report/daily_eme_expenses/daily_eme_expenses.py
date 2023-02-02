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
	total_downtime_ava = frappe._dict({"expense_head":"Total Downtime"})
	total_downtime_uti = frappe._dict({"expense_head":"Total unproductive time loss"})
	# assin 0 value for all columns total sum of hours
	for p in period_list:
		total_actual_hours[str(p.key)] = 0
		total_downtime_ava[str(p.key)] = 0
		total_downtime_uti[str(p.key)] = 0
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
									GROUP BY li.uom""", {"posting_date": getdate(p.key), "expense_head": exp.name, "eqp": filters.equipment}, as_dict=1)
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
	data.append({})
	data.append(total_actual_hours)
	data.append({})

	data.append(frappe._dict({"expense_head":"Performance Record"}))
	schedule_hr 	= frappe._dict({"expense_head":"Scheduled Hour"})

	for p in period_list:
		scheduled_working_hour = frappe.db.sql('''
			SELECT MAX(scheduled_working_hour) as swh FROM `tabLogbook` 
			WHERE docstatus = 1 AND posting_date = '{}'
				AND equipment = '{}'
			'''.format(getdate(p.key), filters.equipment))

		if scheduled_working_hour:
			schedule_hr[str(p.key)] = scheduled_working_hour[0][0] if scheduled_working_hour[0][0] else 0
	data.append(schedule_hr)
	# for downtime type availability
	for d in get_downtime_reason("Availability"):
		downtime_ava 	= frappe._dict({"reading":d.downtime_reason})
		flg = False
		for p in period_list:
			hrs = frappe.db.sql('''
					SELECT SUM(di.hours) as hrs
					FROM `tabLogbook` l INNER JOIN `tabDowntime Item` di ON l.name = di.parent
					WHERE l.docstatus = 1 AND l.posting_date = '{}'
					AND l.equipment = '{}' AND di.downtime_reason = '{}'
			'''.format(getdate(p.key), filters.equipment, d.offence))
			if hrs:
				if hrs[0][0]:
					flg = True
					downtime_ava[str(p.key)] = hrs[0][0]
				else:
					downtime_ava[str(p.key)] = 0
				total_downtime_ava[str(p.key)] += flt(downtime_ava[str(p.key)])
		if flg:
			data.append(downtime_ava)
	data.append(total_downtime_ava)
	availability 	= frappe._dict({"expense_head":"Availability (Scheduled Hour - Total Downtime)"})
	for p in period_list:
		availability[str(p.key)] = flt(schedule_hr[str(p.key)]) - flt(total_downtime_ava[str(p.key)])

	data.append(availability)
	data.append({})
	# for downtime type utilization
	for d in get_downtime_reason("Utilization"):
		downtime_uti	= frappe._dict({"reading":d.downtime_reason})
		flg = False
		for p in period_list:
			hrs = frappe.db.sql('''
					SELECT SUM(di.hours) as hrs
					FROM `tabLogbook` l INNER JOIN `tabDowntime Item` di ON l.name = di.parent
					WHERE l.docstatus = 1 AND l.posting_date = '{}'
					AND l.equipment = '{}' AND di.downtime_reason = '{}'
			'''.format(getdate(p.key), filters.equipment, d.offence))

			if hrs:
				if hrs[0][0]:
					flg = True
					downtime_uti[str(p.key)] = hrs[0][0]
				else:
					downtime_uti[str(p.key)] = 0

			total_downtime_uti[str(p.key)] += flt(downtime_uti[str(p.key)])
		if flg:
			data.append(downtime_uti)

	data.append(total_downtime_uti)
	utilization 	= frappe._dict({"expense_head":"Utilization (Scheduled Hour - Total unproductive time loss)"})
	for p in period_list:
		utilization[str(p.key)] = flt(schedule_hr[str(p.key)]) - flt(total_downtime_uti[str(p.key)])
	data.append(utilization)

	for d in get_offence():
		offence = frappe._dict({"reading":d.offence})
		flg = False
		for p in period_list:
			offence_count = frappe.db.sql('''
				select count(1) from `tabIncident Report` where equipment = '{}' and  docstatus = 1 and offence_date = '{}' and offence = '{}'
			'''.format(filters.equipment,getdate(p.key), d.offence))
			if offence_count:
				if offence_count[0][0]:
					flg = True
					offence[str(p.key)] = offence_count[0][0]
				else:
					offence[str(p.key)] = 0
		if flg:
			data.append(offence)
	return data

def get_downtime_reason(downtime_type):
	downtime_reason = qb.DocType("Downtime Reason")
	return (qb.from_(downtime_reason).select(downtime_reason.downtime_reason.as_("offence")).where((downtime_reason.type == downtime_type) & (downtime_reason.disabled == 0))).run(as_dict=1)
def get_eme_expenses():
	exp_head = qb.DocType("Expense Head")
	return (qb.from_(exp_head).select(exp_head.name).where(exp_head.disabled==0).orderby(exp_head.order_index)).run(as_dict=1)

def get_per_ava():
	dr = qb.DocType("Downtime Reason")
	return (qb.from_(dr).select(dr.name, dr.type.as_("reason_type").where(dr.disabled==0).orderby(dr.type))).run(as_dict=1)

def get_offence():
	of = qb.DocType("Offence")
	return (qb.from_(of).select(of.name.as_("offence")).where(of.disabled==0)).run(as_dict=1)

def get_columns(filters, period_list):
	columns = []
	columns.append({"fieldname":"expense_head",
					"fieldtype":"Data",
					"label":"Expense Head",
					"width":300})
	columns.append({"fieldname":"reading",
					"fieldtype":"Data",
					"label":"Reading",
					"width":150})
	for p in period_list:
		columns.append({
			"fieldname":str(p.key),
			"label":p.label,
			"fieldtype":"Float"
		})
	return columns

