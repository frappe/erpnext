# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(report_filters):
	data = []
	operations = frappe.get_all("Operation", filters = {"is_corrective_operation": 1})
	if operations:

		if report_filters.get('operation'):
			operations = [report_filters.get('operation')]
		else:
			operations = [d.name for d in operations]

		job_card_time_log = frappe.qb.DocType("Job Card Time Log")
		job_card = frappe.qb.DocType("Job Card")
		operatingcost = ((job_card.hour_rate) * (job_card.total_time_in_mins) / 60.0).as_('operating_cost')
		itemcode = (job_card.production_item).as_('item_code')
		query = (frappe.qb.from_(job_card)
				.select(job_card.name, job_card.work_order, itemcode, job_card.item_name, job_card.operation,
				job_card.serial_no, job_card.batch_no, job_card.workstation, job_card.total_time_in_mins, job_card.hour_rate,
				operatingcost)
				.where(job_card.docstatus==1)
				.where(job_card.is_corrective_job_card==1)
				.where(job_card.name.isin(
					frappe.qb.from_(job_card_time_log)
					.select(job_card_time_log.parent)
					.where(job_card_time_log.parent == job_card.name)
					.where(job_card_time_log.from_time >= report_filters.get('from_date',''))
					.where(job_card_time_log.to_time <= report_filters.get('to_date',''))
												)
					)
				)
		query = append_filters(report_filters,operations,query,job_card)
		data = query.run()
	return data

def append_filters(report_filters, operations,query,job_Card):
	for field in ["name", "work_order", "operation", "workstation", "company", "serial_no", "batch_no", "production_item"]:
		if report_filters.get(field):
			if field == 'serial_no':
				query = query.where(job_Card[field].like('%{}%'.format(report_filters.get(field))))
			elif field == 'operation':
				query = query.where(job_Card[field].isin(operations))
			else:
				query = query.where(job_Card[field] ==report_filters.get(field))
	return query

def get_columns(filters):
	return [
		{
			"label": _("Job Card"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Job Card",
			"width": "120"
		},
		{
			"label": _("Work Order"),
			"fieldtype": "Link",
			"fieldname": "work_order",
			"options": "Work Order",
			"width": "100"
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": "100"
		},
		{
			"label": _("Item Name"),
			"fieldtype": "Data",
			"fieldname": "item_name",
			"width": "100"
		},
		{
			"label": _("Operation"),
			"fieldtype": "Link",
			"fieldname": "operation",
			"options": "Operation",
			"width": "100"
		},
		{
			"label": _("Serial No"),
			"fieldtype": "Data",
			"fieldname": "serial_no",
			"width": "100"
		},
		{
			"label": _("Batch No"),
			"fieldtype": "Data",
			"fieldname": "batch_no",
			"width": "100"
		},
		{
			"label": _("Workstation"),
			"fieldtype": "Link",
			"fieldname": "workstation",
			"options": "Workstation",
			"width": "100"
		},
		{
			"label": _("Operating Cost"),
			"fieldtype": "Currency",
			"fieldname": "operating_cost",
			"width": "150"
		},
		{
			"label": _("Total Time (in Mins)"),
			"fieldtype": "Float",
			"fieldname": "total_time_in_mins",
			"width": "150"
		}
	]
