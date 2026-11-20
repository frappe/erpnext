# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Locate
from frappe.utils import flt, get_datetime
from pypika.terms import ExistsCriterion

from erpnext.accounts.report.utils import validate_date_range
from erpnext.manufacturing.doctype.job_card.job_card import get_workstation_minutes
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def execute(filters=None):
	validate_date_range(filters)
	return get_columns(filters), get_data(filters)


def get_data(report_filters):
	data = []
	operations = frappe.get_all("Operation", filters={"is_corrective_operation": 1})
	if operations:
		if report_filters.get("operation"):
			operations = [report_filters.get("operation")]
		else:
			operations = [d.name for d in operations]

		job_card = frappe.qb.DocType("Job Card")

		operating_cost = ((job_card.hour_rate) * (job_card.total_time_in_mins) / 60.0).as_("operating_cost")
		item_code = (job_card.production_item).as_("item_code")

		query = (
			frappe.qb.from_(job_card)
			.select(
				job_card.name,
				job_card.work_order,
				item_code,
				job_card.item_name,
				job_card.operation,
				job_card.serial_no,
				job_card.batch_no,
				job_card.workstation,
				job_card.total_time_in_mins,
				job_card.hour_rate,
				operating_cost,
			)
			.where((job_card.docstatus == 1) & (job_card.is_corrective_job_card == 1))
		)

		query = append_filters(query, report_filters, operations, job_card)
		data = query.run(as_dict=True)
		if report_filters.get("serial_no"):
			data = keep_exact_serial_no(data, report_filters.get("serial_no"))
		if report_filters.get("from_date") or report_filters.get("to_date"):
			clip_to_date_range(data, report_filters)
	return data


def append_filters(query, report_filters, operations, job_card):
	"""Append optional filters to query builder."""

	for field in (
		"name",
		"work_order",
		"operation",
		"workstation",
		"company",
		"serial_no",
		"batch_no",
		"production_item",
	):
		if report_filters.get(field):
			if field == "serial_no":
				query = query.where(Locate(report_filters.get(field), job_card[field]) > 0)
			elif field == "operation":
				query = query.where(job_card[field].isin(operations))
			else:
				query = query.where(job_card[field] == report_filters.get(field))

	if report_filters.get("from_date") or report_filters.get("to_date"):
		query = query.where(ExistsCriterion(get_overlapping_time_logs(report_filters, job_card)))

	return query


def get_overlapping_time_logs(report_filters, job_card):
	time_log = frappe.qb.DocType("Job Card Time Log")
	query = (
		frappe.qb.from_(time_log)
		.select(time_log.name)
		.where((time_log.parent == job_card.name) & (time_log.parenttype == "Job Card"))
	)
	if report_filters.get("from_date"):
		query = query.where(time_log.to_time > report_filters.get("from_date"))
	if report_filters.get("to_date"):
		query = query.where(time_log.from_time < report_filters.get("to_date"))

	return query


def clip_to_date_range(data, report_filters):
	if not data:
		return

	start = get_datetime(report_filters.get("from_date")) if report_filters.get("from_date") else None
	end = get_datetime(report_filters.get("to_date")) if report_filters.get("to_date") else None

	time_logs = defaultdict(list)
	for log in frappe.get_all(
		"Job Card Time Log",
		filters={
			"parent": ["in", [row.name for row in data]],
			"parenttype": "Job Card",
			"from_time": ["is", "set"],
			"to_time": ["is", "set"],
		},
		fields=["parent", "from_time", "to_time"],
	):
		if clipped_log := clip_time_log(log, start, end):
			time_logs[log.parent].append(clipped_log)

	for row in data:
		# union of the intervals, so parallel operators count once, as in the Job Card
		minutes = get_workstation_minutes(time_logs[row.name])
		row.total_time_in_mins = flt(minutes, 2)
		row.operating_cost = flt(row.hour_rate) * minutes / 60.0


def clip_time_log(log, start, end):
	from_time, to_time = get_datetime(log.from_time), get_datetime(log.to_time)
	from_time, to_time = max(from_time, start or from_time), min(to_time, end or to_time)
	return frappe._dict(from_time=from_time, to_time=to_time) if from_time < to_time else None


def keep_exact_serial_no(data, serial_no):
	return [row for row in data if serial_no in get_serial_nos(row.serial_no)]


def get_columns(filters):
	return [
		{
			"label": _("Job Card"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Job Card",
			"width": "120",
		},
		{
			"label": _("Work Order"),
			"fieldtype": "Link",
			"fieldname": "work_order",
			"options": "Work Order",
			"width": "100",
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": "100",
		},
		{"label": _("Item Name"), "fieldtype": "Data", "fieldname": "item_name", "width": "100"},
		{
			"label": _("Operation"),
			"fieldtype": "Link",
			"fieldname": "operation",
			"options": "Operation",
			"width": "100",
		},
		{"label": _("Serial No"), "fieldtype": "Data", "fieldname": "serial_no", "width": "100"},
		{"label": _("Batch No"), "fieldtype": "Data", "fieldname": "batch_no", "width": "100"},
		{
			"label": _("Workstation"),
			"fieldtype": "Link",
			"fieldname": "workstation",
			"options": "Workstation",
			"width": "100",
		},
		{
			"label": _("Operating Cost"),
			"fieldtype": "Currency",
			"fieldname": "operating_cost",
			"width": "150",
		},
		{
			"label": _("Total Time (in Mins)"),
			"fieldtype": "Float",
			"fieldname": "total_time_in_mins",
			"width": "150",
		},
	]
