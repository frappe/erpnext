# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, time_diff_in_hours, get_datetime, time_diff, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class OperationMismatchError(frappe.ValidationError): pass

class JobCard(Document):
	def validate(self):
		self.validate_time_logs()
		self.set_status()
		self.validate_operation_id()

	def validate_time_logs(self):
		self.total_completed_qty = 0.0
		self.total_time_in_mins = 0.0

		if self.get('time_logs'):
			for d in self.get('time_logs'):
				if get_datetime(d.from_time) > get_datetime(d.to_time):
					frappe.throw(_("Row {0}: From time must be less than to time").format(d.idx))

				data = self.get_overlap_for(d)
				if data:
					frappe.throw(_("Row {0}: From Time and To Time of {1} is overlapping with {2}")
						.format(d.idx, self.name, data.name))

				if d.from_time and d.to_time:
					d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
					self.total_time_in_mins += d.time_in_mins

				if d.completed_qty:
					self.total_completed_qty += d.completed_qty

	def get_overlap_for(self, args):
		existing = frappe.db.sql("""select jc.name as name from
			`tabJob Card Time Log` jctl, `tabJob Card` jc where jctl.parent = jc.name and
			(
				(%(from_time)s > jctl.from_time and %(from_time)s < jctl.to_time) or
				(%(to_time)s > jctl.from_time and %(to_time)s < jctl.to_time) or
				(%(from_time)s <= jctl.from_time and %(to_time)s >= jctl.to_time))
			and jctl.name!=%(name)s
			and jc.name!=%(parent)s
			and jc.docstatus < 2
			and jc.employee = %(employee)s """,
			{
				"from_time": args.from_time,
				"to_time": args.to_time,
				"name": args.name or "No Name",
				"parent": args.parent or "No Name",
				"employee": self.employee
			}, as_dict=True)

		return existing[0] if existing else None

	def get_required_items(self):
		if not self.get('work_order'):
			return

		doc = frappe.get_doc('Work Order', self.get('work_order'))
		if doc.transfer_material_against == 'Work Order' or doc.skip_transfer:
			return

		for d in doc.required_items:
			if not d.operation:
				frappe.throw(_("Row {0} : Operation is required against the raw material item {1}")
					.format(d.idx, d.item_code))

			if self.get('operation') == d.operation:
				self.append('items', {
					'item_code': d.item_code,
					'source_warehouse': d.source_warehouse,
					'uom': frappe.db.get_value("Item", d.item_code, 'stock_uom'),
					'item_name': d.item_name,
					'description': d.description,
					'required_qty': (d.required_qty * flt(self.for_quantity)) / doc.qty
				})

	def on_submit(self):
		self.validate_job_card()
		self.update_work_order()
		self.set_transferred_qty()

	def on_cancel(self):
		self.update_work_order()
		self.set_transferred_qty()

	def validate_job_card(self):
		if not self.time_logs:
			frappe.throw(_("Time logs are required for {0} {1}")
				.format(frappe.bold("Job Card"), get_link_to_form("Job Card", self.name)))

		if self.for_quantity and self.total_completed_qty != self.for_quantity:
			total_completed_qty = frappe.bold(_("Total Completed Qty"))
			qty_to_manufacture = frappe.bold(_("Qty to Manufacture"))

			frappe.throw(_("The {0} ({1}) must be equal to {2} ({3})"
				.format(total_completed_qty, frappe.bold(self.total_completed_qty), qty_to_manufacture,frappe.bold(self.for_quantity))))

	def update_work_order(self):
		if not self.work_order:
			return

		for_quantity, time_in_mins = 0, 0
		from_time_list, to_time_list = [], []

		field = "operation_id"
		data = frappe.get_all('Job Card',
			fields = ["sum(total_time_in_mins) as time_in_mins", "sum(total_completed_qty) as completed_qty"],
			filters = {"docstatus": 1, "work_order": self.work_order, field: self.get(field)})

		if data and len(data) > 0:
			for_quantity = data[0].completed_qty
			time_in_mins = data[0].time_in_mins

		if self.get(field):
			time_data = frappe.db.sql("""
				SELECT
					min(from_time) as start_time, max(to_time) as end_time
				FROM `tabJob Card` jc, `tabJob Card Time Log` jctl
				WHERE
					jctl.parent = jc.name and jc.work_order = %s
					and jc.{0} = %s and jc.docstatus = 1
			""".format(field), (self.work_order, self.get(field)), as_dict=1)

			wo = frappe.get_doc('Work Order', self.work_order)

			for data in wo.operations:
				if data.get("name") == self.get(field):
					data.completed_qty = for_quantity
					data.actual_operation_time = time_in_mins
					data.actual_start_time = time_data[0].start_time if time_data else None
					data.actual_end_time = time_data[0].end_time if time_data else None

			wo.flags.ignore_validate_update_after_submit = True
			wo.update_operation_status()
			wo.calculate_operating_cost()
			wo.set_actual_dates()
			wo.save()

	def set_transferred_qty(self, update_status=False):
		if not self.items:
			self.transferred_qty = self.for_quantity if self.docstatus == 1 else 0

		doc = frappe.get_doc('Work Order', self.get('work_order'))
		if doc.transfer_material_against == 'Work Order' or doc.skip_transfer:
			return

		if self.items:
			self.transferred_qty = frappe.db.get_value('Stock Entry', {
				'job_card': self.name,
				'work_order': self.work_order,
				'docstatus': 1
			}, 'sum(fg_completed_qty)') or 0

		self.db_set("transferred_qty", self.transferred_qty)

		qty = 0
		if self.work_order:
			doc = frappe.get_doc('Work Order', self.work_order)
			if doc.transfer_material_against == 'Job Card' and not doc.skip_transfer:
				completed = True
				for d in doc.operations:
					if d.status != 'Completed':
						completed = False
						break

				if completed:
					job_cards = frappe.get_all('Job Card', filters = {'work_order': self.work_order,
						'docstatus': ('!=', 2)}, fields = 'sum(transferred_qty) as qty', group_by='operation_id')

					if job_cards:
						qty = min([d.qty for d in job_cards])

			doc.db_set('material_transferred_for_manufacturing', qty)

		self.set_status(update_status)

	def set_status(self, update_status=False):
		if self.status == "On Hold": return

		self.status = {
			0: "Open",
			1: "Submitted",
			2: "Cancelled"
		}[self.docstatus or 0]

		if self.time_logs:
			self.status = 'Work In Progress'

		if (self.docstatus == 1 and
			(self.for_quantity == self.transferred_qty or not self.items)):
			self.status = 'Completed'

		if self.status != 'Completed':
			if self.for_quantity == self.transferred_qty:
				self.status = 'Material Transferred'

		if update_status:
			self.db_set('status', self.status)

	def validate_operation_id(self):
		if (self.get("operation_id") and self.get("operation_row_number") and self.operation and self.work_order and
			frappe.get_cached_value("Work Order Operation", self.operation_row_number, "name") != self.operation_id):
			work_order = frappe.bold(get_link_to_form("Work Order", self.work_order))
			frappe.throw(_("Operation {0} does not belong to the work order {1}")
				.format(frappe.bold(self.operation), work_order), OperationMismatchError)

@frappe.whitelist()
def get_operation_details(work_order, operation):
	if work_order and operation:
		return frappe.get_all("Work Order Operation", fields = ["name", "idx"],
			filters = {
				"parent": work_order,
				"operation": operation
			}
		)

@frappe.whitelist()
def get_operations(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("work_order"):
		args = {"parent": filters.get("work_order")}
		if txt:
			args["operation"] = ("like", "%{0}%".format(txt))

		return frappe.get_all("Work Order Operation",
			filters = args,
			fields = ["distinct operation as operation"],
			limit_start = start,
			limit_page_length = page_len,
			order_by="idx asc", as_list=1)

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.material_request_type = "Material Transfer"

	doclist = get_mapped_doc("Job Card", source_name, {
		"Job Card": {
			"doctype": "Material Request",
			"field_map": {
				"name": "job_card",
			},
		},
		"Job Card Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"required_qty": "qty",
				"uom": "stock_uom"
			},
			"postprocess": update_item,
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.t_warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.purpose = "Material Transfer for Manufacture"
		target.from_bom = 1
		target.fg_completed_qty = source.get('for_quantity', 0) - source.get('transferred_qty', 0)
		target.calculate_rate_and_amount()
		target.set_missing_values()
		target.set_stock_entry_type()

	doclist = get_mapped_doc("Job Card", source_name, {
		"Job Card": {
			"doctype": "Stock Entry",
			"field_map": {
				"name": "job_card",
				"for_quantity": "fg_completed_qty"
			},
		},
		"Job Card Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"source_warehouse": "s_warehouse",
				"required_qty": "qty",
				"uom": "stock_uom"
			},
			"postprocess": update_item,
		}
	}, target_doc, set_missing_values)

	return doclist

def time_diff_in_minutes(string_ed_date, string_st_date):
	return time_diff(string_ed_date, string_st_date).total_seconds() / 60

@frappe.whitelist()
def get_job_details(start, end, filters=None):
	events = []

	event_color = {
		"Completed": "#cdf5a6",
		"Material Transferred": "#ffdd9e",
		"Work In Progress": "#D3D3D3"
	}

	from frappe.desk.reportview import get_filters_cond
	conditions = get_filters_cond("Job Card", filters, [])

	job_cards = frappe.db.sql(""" SELECT `tabJob Card`.name, `tabJob Card`.work_order,
			`tabJob Card`.employee_name, `tabJob Card`.status, ifnull(`tabJob Card`.remarks, ''),
			min(`tabJob Card Time Log`.from_time) as from_time,
			max(`tabJob Card Time Log`.to_time) as to_time
		FROM `tabJob Card` , `tabJob Card Time Log`
		WHERE
			`tabJob Card`.name = `tabJob Card Time Log`.parent {0}
			group by `tabJob Card`.name""".format(conditions), as_dict=1)

	for d in job_cards:
			subject_data = []
			for field in ["name", "work_order", "remarks", "employee_name"]:
				if not d.get(field): continue

				subject_data.append(d.get(field))

			color = event_color.get(d.status)
			job_card_data = {
				'from_time': d.from_time,
				'to_time': d.to_time,
				'name': d.name,
				'subject': '\n'.join(subject_data),
				'color': color if color else "#89bcde"
			}

			events.append(job_card_data)

	return events
