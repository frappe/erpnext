# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import flt,cstr
from erpnext.accounts.report.financial_statements import get_period_list

def execute(filters=None):
	columns, data, chart = [], [], []
	if filters.get('fiscal_year'):
		company = erpnext.get_default_company()
		period_list = get_period_list(filters.get('fiscal_year'), filters.get('fiscal_year'),"Monthly", company)
		columns=get_columns()
		data=get_log_data(filters)
		chart=get_chart_data(data,period_list)
	return columns, data, None, chart

def get_columns():
	columns = [_("License") + ":Link/Vehicle:100", _('Create') + ":data:50",
		_("Model") + ":data:50", _("Location") + ":data:100",
		_("Log") + ":Link/Vehicle Log:100", _("Odometer") + ":Int:80",
		_("Date") + ":Date:100", _("Fuel Qty") + ":Float:80",
		_("Fuel Price") + ":Float:100",_("Service Expense") + ":Float:100"
	]
	return columns

def get_log_data(filters):
	fy = frappe.db.get_value('Fiscal Year', filters.get('fiscal_year'), ['year_start_date', 'year_end_date'], as_dict=True)
	data = frappe.db.sql("""select
			vhcl.license_plate as "License", vhcl.make as "Make", vhcl.model as "Model",
			vhcl.location as "Location", log.name as "Log", log.odometer as "Odometer",
			log.date as "Date", log.fuel_qty as "Fuel Qty", log.price as "Fuel Price"
		from
			`tabVehicle` vhcl,`tabVehicle Log` log
		where
			vhcl.license_plate = log.license_plate and log.docstatus = 1 and date between %s and %s
		order by date""" ,(fy.year_start_date, fy.year_end_date), as_dict=1)
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

	labels = [period.key for period in period_list]
	fuel_exp_data= [row[1] for row in fueldata]
	service_exp_data= [row[1] for row in servicedata]
	datasets = []
	if fuel_exp_data:
		datasets.append({
			'name': 'Fuel Expenses',
			'values': fuel_exp_data
		})
	if service_exp_data:
		datasets.append({
			'name': 'Service Expenses',
			'values': service_exp_data
		})
	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "line"
	return chart