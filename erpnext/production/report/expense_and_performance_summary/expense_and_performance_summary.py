# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_data(filters):
	data = []
	start_date = filters.from_date
	end_date = filters.to_date
	data.append({
				"expense_head":"Expense Head"
			})
	for a in frappe.db.sql("select name as expense_head from `tabExpense Head` where disabled = 0 order by order_index", as_dict=1):
		cond = get_conditions(filters)
		query ="""
			SELECT sum(li.hours) as hours, 
				li.uom, sum(li.initial_reading) as ir 
			FROM `tabLogbook Item` li
			INNER JOIN `tabLogbook` l 
			ON 
				l.name = li.parent 
			INNER JOIN `tabEquipment` e 
			ON e.name = l.equipment 
			WHERE 
				l.docstatus = 1 
			AND 
				l.posting_date 
			BETWEEN '{}' AND '{}'
			AND 
				li.expense_head = '{}' 
			AND 
				l.branch = '{}' 
			{}  
			GROUP BY li.expense_head, li.uom
			""".format(filters.from_date,filters.to_date,a.expense_head,filters.branch,cond)
		res = frappe.db.sql(query,as_dict=1)
		total_hr = 0
		trip = 0
		days = 0
		for exp in res:
			total_hr = flt(exp.hours) + flt(total_hr)
			if exp.uom == "Trip":
				trip = exp.ir
		if flt(trip) > 0 or flt(total_hr) > 0:
			data.append({
				"expense_head":a.expense_head,
				"hour":flt(total_hr,2),
				"trip":flt(trip,2)
			})
	data.append({})
	data.append({
				"expense_head":"Performance Record"
			})
	availability = 0
	performance = 0
	scheduled_working_hour = 0
	sch_data = frappe.db.sql("""
		SELECT 
			SUM(scheduled_working_hour) as swh 
		FROM tabLogbook l 
		INNER JOIN 
		`tabEquipment` e 
		ON e.name = l.equipment 
		WHERE l.docstatus = 1 
		AND	l.posting_date 
		BETWEEN '{}' AND '{}' 
		AND 
			l.branch = '{}' 
		{}""".format(filters.from_date,filters.to_date,filters.branch,cond))
	if sch_data:
		scheduled_working_hour = sch_data[0][0]
		data.append({
			"expense_head":"Normal working hours",
			"hour":flt(scheduled_working_hour,2)
		})
		
	for p in frappe.db.sql("select name from `tabDowntime Reason` where type = 'Availability'", as_dict=1):
		query = """
			SELECT 
				SUM(di.hours) as hours 
			FROM `tabDowntime Item` di
			INNER JOIN tabLogbook l
			ON l.name = di.parent 
			INNER JOIN `tabEquipment` e 
			ON e.name = l.equipment 
			WHERE l.docstatus = 1 
			AND di.downtime_reason = '{0}' 
			AND l.posting_date between '{1}' 
			AND '{2}' 
			AND l.branch = '{3}' 
			{4}""".format(p.name,filters.from_date,filters.to_date,filters.branch,cond)
		hrs = frappe.db.sql(query)
		if hrs and flt(hrs[0][0]) > 0 :
			data.append({
				"expense_head":p.name,
				"hour":flt(hrs[0][0],2)
			})
			performance = flt(performance) + flt(hrs[0][0])

	data.append({
		"expense_head":"Total Downtime Hours",
		"hour":flt(performance,2)
	})
	data.append({
		"expense_head":"Availability, Hours",
		"hour":flt(flt(scheduled_working_hour) - flt(performance),2)
	})
	data.append({})

	for p in frappe.db.sql("select name from `tabDowntime Reason` where type = 'Utilization'", as_dict=1):
		hrs = frappe.db.sql("""
			SELECT 
				SUM(di.hours) as hours 
			FROM `tabDowntime Item` di
			INNER JOIN `tabLogbook` l 
			ON l.name = di.parent 
			INNER JOIN `tabEquipment` e 
			ON e.name = l.equipment 
			WHERE l.docstatus = 1 
			AND di.downtime_reason = '{}' 
			AND l.posting_date between '{}' 
			AND '{}' 
			AND l.branch = '{}' 
			{}""".format(p.name,filters.from_date,filters.to_date,filters.branch,cond))
		if hrs and flt(hrs[0][0]) > 0:
			data.append({
				"expense_head":p.name,
				"hour":flt(hrs[0][0],2)
			})
			availability = flt(availability) + flt(hrs[0][0])
		
	data.append({
				"expense_head":"Total unproductive time loss, Hours",
				"hour":flt(availability,2)
			})
	data.append({
				"expense_head":"Utilization, Hours",
				"hour":flt(flt(scheduled_working_hour) - flt(performance) - flt(availability),2)
			})
	
	data.append({})
	for p in frappe.db.sql("select name from `tabOffence`", as_dict=1):
		hrs = frappe.db.sql("""
		SELECT count(1) as no 
		FROM `tabIncident Report` i 
		INNER JOIN `tabEquipment` e 
			ON e.name = i.equipment 
		WHERE i.docstatus = 1 
		AND i.offence_date 
		BETWEEN '{}' 
		AND '{}' 
		AND e.branch = '{}' 
		{} 
		AND i.offence = '{}'""".format(filters.from_date,filters.to_date,filters.branch,cond,p.name))
		if hrs and flt(hrs[0][0]) > 0:
			data.append({
				"expense_head":p.name,
				"hour":flt(hrs[0][0],2)
			})
	return data

def get_conditions(filters):
	cond = ""
	if filters.from_date > filters.to_date:
		frappe.throw("From Date cannot be greater than To Date")
	if filters.supplier and filters.company_owned:
		frappe.throw("There wont be Vendor for Company owned Equipment")
	if filters.supplier:
		cond += " AND e.supplier = '{}'".format(filters.supplier)

	if filters.equipment:
		cond+= " AND e.name = '{}'".format(filters.equipment)

	if filters.equipment_type:
		cond += " AND e.equipment_type = '{}'".format(filters.equipment_type)

	if filters.company_owned:
		cond += " AND e.hired_equipment = 0"
	return cond

def get_columns():
	columns = []
	columns.append({"fieldname":"expense_head",
					"fieldtype":"Data",
					"label":"Expense Head",
					"width":300})
	columns.append({"fieldname":"hour",
					"fieldtype":"Data",
					"label":"Hour",
					"width":150})
	columns.append({"fieldname":"trip",
					"fieldtype":"Data",
					"label":"Trip",
					"width":150})
	return columns