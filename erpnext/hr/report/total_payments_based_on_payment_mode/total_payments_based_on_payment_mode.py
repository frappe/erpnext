# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.regional.report.provident_fund_deductions.provident_fund_deductions import get_conditions

def execute(filters=None):
	mode_of_payments = get_payment_modes()
	columns = get_columns(filters, mode_of_payments)
	data = get_data(filters, mode_of_payments)

	return columns, data

def get_columns(filters, mode_of_payments):
	columns = [{
		"label": _("Branch"),
		"options": "Branch",
		"fieldname": "branch",
		"fieldtype": "Link",
		"width": 200
	}]

	for mode in mode_of_payments:
		columns.append({
			"label": _(mode),
			"fieldname": mode,
			"fieldtype": "Currency",
			"width": 160
		})

	columns.append({
		"label": _("Total"),
		"fieldname": "total",
		"fieldtype": "Currency",
		"width": 140
	})

	return columns

def get_payment_modes():
	mode_of_payments = frappe.db.sql_list(""" 
		select distinct mode_of_payment from `tabSalary Slip` where docstatus = 1
	""")
	
	return mode_of_payments

def prepare_data(entry):
	branch_wise_entries = {}
	gross_pay = 0 

	for d in entry:
		gross_pay += d.gross_pay
		if branch_wise_entries.get(d.branch):
			branch_wise_entries[d.branch][d.mode_of_payment] = d.net_pay
		else:
			branch_wise_entries.setdefault(d.branch, {}).setdefault(d.mode_of_payment, d.net_pay)

	return branch_wise_entries, gross_pay

def get_data(filters, mode_of_payments):
	data = []

	conditions = get_conditions(filters)

	entry = frappe.db.sql("""
		select branch, mode_of_payment, sum(net_pay) as net_pay, sum(gross_pay) as gross_pay
		from `tabSalary Slip` sal
		where docstatus = 1 %s
		group by branch, mode_of_payment
		""" % (conditions), as_dict=1)

	branch_wise_entries, gross_pay = prepare_data(entry)

	branches = frappe.db.sql_list("""
		select distinct branch from `tabSalary Slip` sal
		where docstatus = 1 %s
	""" % (conditions))

	total_row = {"total": 0, "branch": "Total"}
	
	for branch in branches:
		total = 0
		row = {
			"branch": branch
		}
		for mode in mode_of_payments:
			if branch_wise_entries.get(branch).get(mode):
				row[mode] = branch_wise_entries.get(branch).get(mode)
				total +=  branch_wise_entries.get(branch).get(mode)

				if total_row.get(mode):
					total_row[mode] += total
				else:
					total_row[mode] = total

		row["total"] = total
		total_row["total"] += total
		data.append(row)

	total_deductions = gross_pay - total_row.get("total")

	if data:
		data.append(total_row)
		data.append({})
		data.append({
			"branch": "Gross Pay",
			mode_of_payments[0]:gross_pay
		})
		data.append({
			"branch": "Total Deductions",
			mode_of_payments[0]:total_deductions
		})
		data.append({
			"branch": "Net Pay",
			mode_of_payments[0]:total_row.get("total")
		})

	return data



