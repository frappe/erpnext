# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
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

		operating_cost = ((job_card.hour_rate) * (job_card.total_time_in_mins) / 60.0).as_(
			"operating_cost"
		)
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
			.groupby(job_card.name)
		)

		query = append_filters(query, report_filters, operations, job_card)
		data = query.run(as_dict=True)
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
				query = query.where(job_card[field].like("%{}%".format(report_filters.get(field))))
			elif field == "operation":
				query = query.where(job_card[field].isin(operations))
			else:
				query = query.where(job_card[field] == report_filters.get(field))

	if report_filters.get("from_date") or report_filters.get("to_date"):
		job_card_time_log = frappe.qb.DocType("Job Card Time Log")

		query = query.join(job_card_time_log).on(job_card.name == job_card_time_log.parent)
		if report_filters.get("from_date"):
			query = query.where(job_card_time_log.from_time >= report_filters.get("from_date"))
		if report_filters.get("to_date"):
			query = query.where(job_card_time_log.to_time <= report_filters.get("to_date"))

	return query


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
