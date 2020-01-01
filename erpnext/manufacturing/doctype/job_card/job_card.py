# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from frappe.utils import (flt, cint, time_diff_in_hours, get_datetime, getdate, 
	get_time, add_to_date, time_diff, add_days, get_datetime_str, get_link_to_form)

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations

class OverlapError(frappe.ValidationError): pass

class JobCard(Document):
	def onload(self):
		if self.get("work_order"):
			work_order_data = frappe.db.get_value("Work Order", self.work_order, 
				["transfer_material_against", "material_consumption_against"], as_dict=1)

			self.set_onload("allow_material_transfer",
				True if work_order_data.transfer_material_against == "Job Card" else False)
			self.set_onload("allow_material_consumption",
				True if work_order_data.material_consumption_against == "Job Card" else False)

	def validate(self):
		self.validate_time_logs()
		self.set_status()

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
						.format(d.idx, self.name, data.name), OverlapError)

				if d.from_time and d.to_time:
					d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
					self.total_time_in_mins += d.time_in_mins

				if d.completed_qty:
					self.total_completed_qty += d.completed_qty

	def get_overlap_for(self, args, check_next_available_slot=False):
		production_capacity = 1
	
		if self.workstation:
			production_capacity = frappe.get_cached_value("Workstation",
				self.workstation, 'production_capacity') or 1
			validate_overlap_for = " and jc.workstation = %(workstation)s "

		if self.employee:
			# override capacity for employee
			production_capacity = 1
			validate_overlap_for = " and jc.employee = %(employee)s "

		extra_cond = ''
		if check_next_available_slot:
			extra_cond = " or (%(from_time)s <= jctl.from_time and %(to_time)s <= jctl.to_time)"

		existing = frappe.db.sql("""select jc.name as name, jctl.to_time from
			`tabJob Card Time Log` jctl, `tabJob Card` jc where jctl.parent = jc.name and
			(
				(%(from_time)s > jctl.from_time and %(from_time)s < jctl.to_time) or
				(%(to_time)s > jctl.from_time and %(to_time)s < jctl.to_time) or
				(%(from_time)s <= jctl.from_time and %(to_time)s >= jctl.to_time) {0}
			)
			and jctl.name != %(name)s and jc.name != %(parent)s and jc.docstatus < 2 {1}
			order by jctl.to_time desc limit 1""".format(extra_cond, validate_overlap_for),
			{
				"from_time": args.from_time,
				"to_time": args.to_time,
				"name": args.name or "No Name",
				"parent": args.parent or "No Name",
				"employee": self.employee,
				"workstation": self.workstation
			}, as_dict=True)

		if existing and production_capacity > len(existing):
			return

		return existing[0] if existing else None

	def schedule_time_logs(self, row):
		row.remaining_time_in_mins = row.time_in_mins
		while row.remaining_time_in_mins > 0:
			args = frappe._dict({
				"from_time": row.planned_start_time,
				"to_time": row.planned_end_time
			})

			self.validate_overlap_for_workstation(args, row)
			self.check_workstation_time(row)

	def validate_overlap_for_workstation(self, args, row):
		# get the last record based on the to time from the job card
		data = self.get_overlap_for(args, check_next_available_slot=True)
		if data:
			row.planned_start_time = get_datetime(data.to_time + get_mins_between_operations())

	def check_workstation_time(self, row):
		workstation_doc = frappe.get_cached_doc("Workstation", self.workstation)
		if (not workstation_doc.working_hours or
			cint(frappe.db.get_single_value("Manufacturing Settings", "allow_overtime"))):
			row.remaining_time_in_mins -= time_diff_in_minutes(row.planned_end_time,
				row.planned_start_time)

			self.update_time_logs(row)
			return

		start_date = getdate(row.planned_start_time)
		start_time = get_time(row.planned_start_time)

		new_start_date = workstation_doc.validate_workstation_holiday(start_date)

		if new_start_date != start_date:
			row.planned_start_time = datetime.datetime.combine(new_start_date, start_time)
			start_date = new_start_date

		total_idx = len(workstation_doc.working_hours)

		for i, time_slot in enumerate(workstation_doc.working_hours):
			workstation_start_time = datetime.datetime.combine(start_date, get_time(time_slot.start_time))
			workstation_end_time = datetime.datetime.combine(start_date, get_time(time_slot.end_time))

			if (get_datetime(row.planned_start_time) >= workstation_start_time and
				get_datetime(row.planned_start_time) <= workstation_end_time):
				time_in_mins = time_diff_in_minutes(workstation_end_time, row.planned_start_time)

				# If remaining time fit in workstation time logs else split hours as per workstation time
				if time_in_mins > row.remaining_time_in_mins:
					row.planned_end_time = add_to_date(row.planned_start_time,
						minutes=row.remaining_time_in_mins)
					row.remaining_time_in_mins = 0
				else:
					row.planned_end_time = add_to_date(row.planned_start_time, minutes=time_in_mins)
					row.remaining_time_in_mins -= time_in_mins

				self.update_time_logs(row)

				if total_idx != (i+1) and row.remaining_time_in_mins > 0:
					row.planned_start_time = datetime.datetime.combine(start_date,
						get_time(workstation_doc.working_hours[i+1].start_time))

		if row.remaining_time_in_mins > 0:
			start_date = add_days(start_date, 1)
			row.planned_start_time = datetime.datetime.combine(start_date,
				get_time(workstation_doc.working_hours[0].start_time))

	def update_time_logs(self, row):
		self.append("time_logs", {
			"from_time": row.planned_start_time,
			"to_time": row.planned_end_time,
			"completed_qty": 0,
			"time_in_mins": time_diff_in_minutes(row.planned_end_time, row.planned_start_time),
		})

	def get_required_items(self):
		if not self.get("work_order"):
			return

		doc = frappe.get_doc("Work Order", self.get("work_order"))
		if not (doc.transfer_material_against == "Job Card" or
			doc.material_consumption_against == "Job Card") or doc.skip_transfer:
			return

		for d in doc.required_items:
			if not d.operation:
				frappe.throw(_("Row {0} : Operation is required against the raw material item {1}")
					.format(d.idx, d.item_code))

			if self.get("operation") == d.operation:
				self.append("items", {
					"item_code": d.item_code,
					"source_warehouse": d.source_warehouse,
					"uom": frappe.db.get_value("Item", d.item_code, "stock_uom"),
					"item_name": d.item_name,
					"description": d.description,
					"required_qty": (d.required_qty * flt(self.for_quantity)) / doc.qty
				})

	def on_submit(self):
		self.validate_job_card()
		self.update_work_order()

	def on_cancel(self):
		self.update_work_order()

	def validate_job_card(self):
		if not self.time_logs:
			frappe.throw(_("Time logs are required for job card {0}").format(self.name))

		if self.total_completed_qty <= 0.0:
			frappe.throw(_("Total completed qty must be greater than zero"))

		if self.total_completed_qty != self.for_quantity:
			frappe.throw(_("The total completed qty({0}) must be equal to qty to manufacture({1})"
				.format(frappe.bold(self.total_completed_qty),frappe.bold(self.for_quantity))))

	def update_work_order(self):
		if not self.work_order:
			return

		for_quantity, time_in_mins = 0, 0
		from_time_list, to_time_list = [], []

		for d in frappe.get_all('Job Card',
			filters = {'docstatus': 1, 'operation_id': self.operation_id}):
			doc = frappe.get_doc('Job Card', d.name)

			for_quantity += doc.total_completed_qty
			time_in_mins += doc.total_time_in_mins
			for time_log in doc.time_logs:
				if time_log.from_time:
					from_time_list.append(time_log.from_time)
				if time_log.to_time:
					to_time_list.append(time_log.to_time)

		wo = frappe.get_doc('Work Order', self.work_order)

		for data in wo.operations:
			if data.name == self.operation_id:
				data.completed_qty = for_quantity
				data.actual_operation_time = time_in_mins
				data.actual_start_time = min(from_time_list) if from_time_list else None
				data.actual_end_time = max(to_time_list) if to_time_list else None

		wo.flags.ignore_validate_update_after_submit = True
		wo.update_operation_status()
		wo.calculate_operating_cost()
		wo.set_actual_dates()
		wo.save()

	def set_status(self, update=False):
		if self.status == "On Hold": return

		self.status = {
			0: "Open",
			1: "Submitted",
			2: "Cancelled"
		}[self.docstatus or 0]

		if self.time_logs:
			self.status = 'Work In Progress'

		if self.per_transferred == 100:
			self.status = 'Material Transferred'

		if self.docstatus == 1:
			if self.per_transferred == 100 and self.per_consumed == 100:
				self.status = 'Completed'

		if update:
			self.db_set('status', self.status)

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
				"operation_id": "operation_id"
			},
		},
		"Job Card Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"required_qty": "qty",
				"uom": "stock_uom",
				"uom": "uom",
				"name": "job_card_item",
				"parent": "job_card",
			},
			"postprocess": update_item,
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_stock_entry(source_name, purpose):
	message = {
		"Material Transfer for Manufacture": "Materials are transferred from source to work in progress warehouse",
		"Material Consumption for Manufacture": "Materials are consumed from the work in progress warehouse"
	}

	doc = _make_stock_entry(source_name, purpose=purpose)
	doc.submit()

	frappe.msgprint(_("{0}, check {1}")
		.format(message.get(purpose), get_link_to_form("Stock Entry", doc.name)))

@frappe.whitelist()
def _make_stock_entry(source_name, target_doc=None, purpose=None):
	def update_item(obj, target, source_parent):
		target.s_warehouse = source_parent.wip_warehouse
		target.qty = obj.required_qty - obj.consumed_qty
		if purpose == "Material Transfer for Manufacture":
			target.qty = obj.required_qty - obj.transferred_qty
			target.s_warehouse = obj.source_warehouse
			target.t_warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.from_bom = 1
		target.purpose = purpose
		target.fg_completed_qty = source.get("for_quantity", 0)
		target.calculate_rate_and_amount()
		target.set_missing_values()
		target.set_stock_entry_type()
		
		if (purpose == "Material Consumption for Manufacture" and
			frappe.db.get_single_value("Manufacturing Settings",
				"backflush_raw_materials_based_on") == "Material Transferred for Manufacture"):
			target.items = []
			target.get_transfered_raw_materials(source_name)

	doclist = get_mapped_doc("Job Card", source_name, {
		"Job Card": {
			"doctype": "Stock Entry",
			"field_map": {
				"name": "job_card",
				"for_quantity": "fg_completed_qty",
				"operation_id": "operation_id"
			},
		},
		"Job Card Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"name": "job_card_item",
				"parent": "job_card",
				"uom": "stock_uom",
				"uom": "uom"
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
