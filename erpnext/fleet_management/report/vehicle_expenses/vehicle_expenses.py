# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt,cstr
from erpnext.accounts.report.financial_statements import get_period_list

def execute(filters=None):
	period_list = get_period_list(2016, 2016,"Monthly")
	for period in period_list:
		pass
	columns, data = [], []
	columns=get_columns()
	data=get_log_data(filters)
	chart=get_chart_data(data,period_list)
	return columns,data,None,chart
	
def get_columns():
	columns = [_("License") + ":Link/Vehicle:100", _("Make") + ":data:50",
				_("Model") + ":data:50", _("Location") + ":data:100",
				_("Log") + ":Link/Vehicle Log:100", _("Odometer") + ":Int:80",
				_("Date") + ":Date:100", _("Fuel Qty") + ":Float:80",
				_("Fuel Price") + ":Float:100",_("Service Expense") + ":Float:100"
	]
	return columns

def get_log_data(filters):
	conditions=""
	if filters.from_date:
		conditions += " and date >= %(from_date)s"
	if filters.to_date:
		conditions += " and date <= %(to_date)s"
	data = frappe.db.sql("""select vhcl.license_plate as "License",vhcl.make as "Make",vhcl.model as "Model",
							vhcl.location as "Location",log.name as "Log",log.odometer as "Odometer",log.date as "Date",
							log.fuel_qty as "Fuel Qty",log.price as "Fuel Price"
							from `tabVehicle` vhcl,`tabVehicle Log` log
							where vhcl.license_plate = log.license_plate and log.docstatus = 1 %s
							order by date""" % (conditions,),filters, as_dict=1)
	dl=list(data)
	for row in dl:
		row["Service Expense"]= get_service_expense(row["Log"])
	return dl
	
def get_service_expense(logname):
	expense_amount = frappe.db.sql("""select sum(expense_amount) 
										from `tabVehicle Log` log,`tabVehicle Service` ser 
										where ser.parent=log.name and log.name=%s""",logname)
	return flt(expense_amount[0][0]) if expense_amount else 0
	
def get_chart_data(data,period_list):
	fuel_exp_data,service_exp_data,fueldata,servicedata = [],[],[],[]
	service_exp_data = []
	fueldata = []
	for period in period_list:
		total_fuel_exp=0
		total_ser_exp=0
		for row in data:
			if row["Date"] <= period.to_date and row["Date"] >= period.from_date:
				total_fuel_exp+=flt(row["Fuel Price"])
				total_ser_exp+=flt(row["Service Expense"])
		fueldata.append([period.key,total_fuel_exp])
		servicedata.append([period.key,total_ser_exp])

	x_intervals = ['x'] + [period.key for period in period_list]
	fuel_exp_data= [row[1] for row in fueldata]
	service_exp_data= [row[1] for row in servicedata]
	columns = [x_intervals]
	if fuel_exp_data:
		columns.append(["Fuel Expenses"]+ fuel_exp_data)
	if service_exp_data:
		columns.append(["Service Expenses"]+ service_exp_data)
	chart = {
		"data": {
			'x': 'x',
			'columns': columns
		}
	}
	chart["chart_type"] = "line"
	return chart