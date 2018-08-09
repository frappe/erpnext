# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, time_diff_in_hours, get_datetime
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class JobCard(Document):
	def validate(self):
		self.validate_actual_dates()

	def validate_actual_dates(self):
		if get_datetime(self.actual_start_date) > get_datetime(self.actual_end_date):
			frappe.throw(_("Actual start date must be less than actual end date"))

		if not (self.employee and self.actual_start_date and self.actual_end_date):
			return

		data = frappe.db.sql(""" select name from `tabJob Card`
			where
				((%(actual_start_date)s > actual_start_date and %(actual_start_date)s < actual_end_date) or
				(%(actual_end_date)s > actual_start_date and %(actual_end_date)s < actual_end_date) or
				(%(actual_start_date)s <= actual_start_date and %(actual_end_date)s >= actual_end_date)) and
				name != %(name)s and employee = %(employee)s and docstatus =1
		""", self.as_dict(), as_dict=1)

		if data:
			frappe.throw(_("Start date and end date is overlapping with the job card <a href='#Form/Job Card/{0}'>{1}</a>")
				.format(data[0].name, data[0].name))

	def get_required_items(self):
		if not self.get('work_order'):
			return

		doc = frappe.get_doc('Work Order', self.get('work_order'))
		if not doc.transfer_material_against_job_card:
			return

		for d in doc.required_items:
			if not d.operation:
				frappe.throw(_("Row {0} : Operation is required against the raw material item {1}")
					.format(d.idx, d.item_code))

			if self.get('operation') == d.operation:
				child = self.append('items', {
					'item_code': d.item_code,
					'source_warehouse': d.source_warehouse,
					'uom': frappe.db.get_value("Item", d.item_code, 'stock_uom'),
					'item_name': d.item_name,
					'description': d.description,
					'required_qty': (d.required_qty * flt(self.for_quantity)) / doc.qty
				})

	def on_submit(self):
		self.validate_dates()
		self.update_work_order()

	def validate_dates(self):
		if not self.actual_start_date and not self.actual_end_date:
			frappe.throw(_("Actual start date and actual end date is mandatory"))

	def on_cancel(self):
		self.update_work_order(cancel=True)

	def update_work_order(self, cancel=False):
		if not self.work_order:
			return

		wo = frappe.get_doc('Work Order', self.work_order)

		for data in wo.operations:
			if data.name == self.operation_id:
				if cancel:
					data.completed_qty -= self.for_quantity
					data.actual_operation_time -= time_diff_in_hours(self.actual_end_date, self.actual_start_date) * 60
					data.actual_start_time = None
					data.actual_end_time = None
				else:
					data.completed_qty = self.for_quantity
					data.actual_operation_time = time_diff_in_hours(self.actual_end_date, self.actual_start_date) * 60
					data.actual_start_time = get_datetime(self.actual_start_date)
					data.actual_end_time = get_datetime(self.actual_end_date)

		wo.flags.ignore_validate_update_after_submit = True
		wo.update_operation_status()
		wo.calculate_operating_cost()
		wo.set_actual_dates()
		wo.save()

def update_job_card_reference(name, fieldname, value):
	frappe.db.set_value('Job Card', name, fieldname, value)

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.warehouse = source_parent.wip_warehouse

	def set_missing_values(source, target):
		target.material_request_type = "Material Transfer"

	doclist = get_mapped_doc("Job Card", source_name, {
		"Job Card": {
			"doctype": "Material Request",
			"validation": {
				"docstatus": ["=", 1]
			},
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
		target.calculate_rate_and_amount()
		target.set_missing_values()

	doclist = get_mapped_doc("Job Card", source_name, {
		"Job Card": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1]
			},
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
