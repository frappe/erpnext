# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import getdate
from pypika import functions as fn


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{
			"label": _("Date of Joining"),
			"fieldname": "date_of_joining",
			"fieldtype": "Date",
			"width": 120,
		},
		{"label": _("Relieving Date"), "fieldname": "relieving_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Exit Interview"),
			"fieldname": "exit_interview",
			"fieldtype": "Link",
			"options": "Exit Interview",
			"width": 150,
		},
		{
			"label": _("Interview Status"),
			"fieldname": "interview_status",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Final Decision"),
			"fieldname": "employee_status",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Full and Final Statement"),
			"fieldname": "full_and_final_statement",
			"fieldtype": "Link",
			"options": "Full and Final Statement",
			"width": 180,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 120,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 120,
		},
		{
			"label": _("Reports To"),
			"fieldname": "reports_to",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
	]


def get_data(filters):
	employee = frappe.qb.DocType("Employee")
	interview = frappe.qb.DocType("Exit Interview")
	fnf = frappe.qb.DocType("Full and Final Statement")

	query = (
		frappe.qb.from_(employee)
		.left_join(interview)
		.on(interview.employee == employee.name)
		.left_join(fnf)
		.on(fnf.employee == employee.name)
		.select(
			employee.name.as_("employee"),
			employee.employee_name.as_("employee_name"),
			employee.date_of_joining.as_("date_of_joining"),
			employee.relieving_date.as_("relieving_date"),
			employee.department.as_("department"),
			employee.designation.as_("designation"),
			employee.reports_to.as_("reports_to"),
			interview.name.as_("exit_interview"),
			interview.status.as_("interview_status"),
			interview.employee_status.as_("employee_status"),
			interview.reference_document_name.as_("questionnaire"),
			fnf.name.as_("full_and_final_statement"),
		)
		.distinct()
		.where(
			(fn.Coalesce(fn.Cast(employee.relieving_date, "char"), "") != "")
			& ((interview.name.isnull()) | ((interview.name.isnotnull()) & (interview.docstatus != 2)))
			& ((fnf.name.isnull()) | ((fnf.name.isnotnull()) & (fnf.docstatus != 2)))
		)
		.orderby(employee.relieving_date, order=Order.asc)
	)

	query = get_conditions(filters, query, employee, interview, fnf)
	result = query.run(as_dict=True)

	return result


def get_conditions(filters, query, employee, interview, fnf):
	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			employee.relieving_date[getdate(filters.get("from_date")) : getdate(filters.get("to_date"))]
		)

	elif filters.get("from_date"):
		query = query.where(employee.relieving_date >= filters.get("from_date"))

	elif filters.get("to_date"):
		query = query.where(employee.relieving_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(employee.company == filters.get("company"))

	if filters.get("department"):
		query = query.where(employee.department == filters.get("department"))

	if filters.get("designation"):
		query = query.where(employee.designation == filters.get("designation"))

	if filters.get("employee"):
		query = query.where(employee.name == filters.get("employee"))

	if filters.get("reports_to"):
		query = query.where(employee.reports_to == filters.get("reports_to"))

	if filters.get("interview_status"):
		query = query.where(interview.status == filters.get("interview_status"))

	if filters.get("final_decision"):
		query = query.where(interview.employee_status == filters.get("final_decision"))

	if filters.get("exit_interview_pending"):
		query = query.where((interview.name == "") | (interview.name.isnull()))

	if filters.get("questionnaire_pending"):
		query = query.where(
			(interview.reference_document_name == "") | (interview.reference_document_name.isnull())
		)

	if filters.get("fnf_pending"):
		query = query.where((fnf.name == "") | (fnf.name.isnull()))

	return query


def get_chart_data(data):
	if not data:
		return None

	retained = 0
	exit_confirmed = 0
	pending = 0

	for entry in data:
		if entry.employee_status == "Employee Retained":
			retained += 1
		elif entry.employee_status == "Exit Confirmed":
			exit_confirmed += 1
		else:
			pending += 1

	chart = {
		"data": {
			"labels": [_("Retained"), _("Exit Confirmed"), _("Decision Pending")],
			"datasets": [{"name": _("Employee Status"), "values": [retained, exit_confirmed, pending]}],
		},
		"type": "donut",
		"colors": ["green", "red", "blue"],
	}

	return chart


def get_report_summary(data):
	if not data:
		return None

	total_resignations = len(data)
	interviews_pending = len([entry.name for entry in data if not entry.exit_interview])
	fnf_pending = len([entry.name for entry in data if not entry.full_and_final_statement])
	questionnaires_pending = len([entry.name for entry in data if not entry.questionnaire])

	return [
		{
			"value": total_resignations,
			"label": _("Total Resignations"),
			"indicator": "Red" if total_resignations > 0 else "Green",
			"datatype": "Int",
		},
		{
			"value": interviews_pending,
			"label": _("Pending Interviews"),
			"indicator": "Blue" if interviews_pending > 0 else "Green",
			"datatype": "Int",
		},
		{
			"value": fnf_pending,
			"label": _("Pending FnF"),
			"indicator": "Blue" if fnf_pending > 0 else "Green",
			"datatype": "Int",
		},
		{
			"value": questionnaires_pending,
			"label": _("Pending Questionnaires"),
			"indicator": "Blue" if questionnaires_pending > 0 else "Green",
			"datatype": "Int",
		},
	]
