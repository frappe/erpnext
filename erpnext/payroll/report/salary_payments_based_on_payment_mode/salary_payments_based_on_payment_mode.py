# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

import erpnext
from erpnext.regional.report.provident_fund_deductions.provident_fund_deductions import (
	get_conditions,
)


def execute(filters=None):
	mode_of_payments = get_payment_modes()

	if not len(mode_of_payments):
		return [], []

	columns = get_columns(filters, mode_of_payments)
	data, total_rows, report_summary = get_data(filters, mode_of_payments)
	chart = get_chart(mode_of_payments, total_rows)

	return columns, data, None, chart, report_summary


def get_columns(filters, mode_of_payments):
	columns = [
		{
			"label": _("Branch"),
			"options": "Branch",
			"fieldname": "branch",
			"fieldtype": "Link",
			"width": 200,
		}
	]

	for mode in mode_of_payments:
		columns.append({"label": _(mode), "fieldname": mode, "fieldtype": "Currency", "width": 160})

	columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 140})

	return columns


def get_payment_modes():
	mode_of_payments = frappe.db.sql_list(
		"""
		select distinct mode_of_payment from `tabSalary Slip` where docstatus = 1
	"""
	)
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

	entry = frappe.db.sql(
		"""
		select branch, mode_of_payment, sum(net_pay) as net_pay, sum(gross_pay) as gross_pay
		from `tabSalary Slip` sal
		where docstatus = 1 %s
		group by branch, mode_of_payment
		"""
		% (conditions),
		as_dict=1,
	)

	branch_wise_entries, gross_pay = prepare_data(entry)

	branches = frappe.db.sql_list(
		"""
		select distinct branch from `tabSalary Slip` sal
		where docstatus = 1 %s
	"""
		% (conditions)
	)

	total_row = {"total": 0, "branch": "Total"}

	for branch in branches:
		total = 0
		row = {"branch": branch}
		for mode in mode_of_payments:
			if branch_wise_entries.get(branch).get(mode):
				row[mode] = branch_wise_entries.get(branch).get(mode)
				total += branch_wise_entries.get(branch).get(mode)

		row["total"] = total
		data.append(row)

	total_row = get_total_based_on_mode_of_payment(data, mode_of_payments)
	total_deductions = gross_pay - total_row.get("total")

	report_summary = []

	if data:
		data.append(total_row)
		data.append({})
		data.append({"branch": "<b>Total Gross Pay</b>", mode_of_payments[0]: gross_pay})
		data.append({"branch": "<b>Total Deductions</b>", mode_of_payments[0]: total_deductions})
		data.append({"branch": "<b>Total Net Pay</b>", mode_of_payments[0]: total_row.get("total")})

		currency = erpnext.get_company_currency(filters.company)
		report_summary = get_report_summary(
			gross_pay, total_deductions, total_row.get("total"), currency
		)

	return data, total_row, report_summary


def get_total_based_on_mode_of_payment(data, mode_of_payments):

	total = 0
	total_row = {"branch": "<b>Total</b>"}
	for mode in mode_of_payments:
		sum_of_payment = sum([detail[mode] for detail in data if mode in detail.keys()])
		total_row[mode] = sum_of_payment
		total += sum_of_payment

	total_row["total"] = total
	return total_row


def get_report_summary(gross_pay, total_deductions, net_pay, currency):
	return [
		{
			"value": gross_pay,
			"label": _("Total Gross Pay"),
			"indicator": "Green",
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": total_deductions,
			"label": _("Total Deduction"),
			"datatype": "Currency",
			"indicator": "Red",
			"currency": currency,
		},
		{
			"value": net_pay,
			"label": _("Total Net Pay"),
			"datatype": "Currency",
			"indicator": "Blue",
			"currency": currency,
		},
	]


def get_chart(mode_of_payments, data):
	if data:
		values = []
		labels = []

		for mode in mode_of_payments:
			values.append(data[mode])
			labels.append([mode])

		chart = {
			"data": {"labels": labels, "datasets": [{"name": "Mode Of Payments", "values": values}]}
		}
		chart["type"] = "bar"
		return chart
