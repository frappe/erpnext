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
	get_time, add_to_date, time_diff, add_days, get_datetime_str)

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations

class OverlapError(frappe.ValidationError): pass

class JobCard(Document):
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
			frappe.throw(_("Time logs are required for job card {0}").format(self.name))

		if self.total_completed_qty <= 0.0:
			frappe.throw(_("Total completed qty must be greater than zero"))

		if self.total_completed_qty > self.for_quantity:
			frappe.throw(_("Total completed qty can not be greater than for quantity"))

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

		if for_quantity:
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