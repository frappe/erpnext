# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CropCycle(Document):
	def validate(self):
		if self.is_new():
			crop = frappe.get_doc('Crop', self.crop)
			self.create_project(crop.period, crop.agriculture_task)
		if not self.project:
			self.project = self.name
		for detected_pest in self.detected_pest:
			pest = frappe.get_doc('Pest', detected_pest.pest)
			self.create_task(pest.treatment_task, self.name, detected_pest.start_date)

	def create_project(self, period, crop_tasks):
		project = frappe.new_doc("Project")
		project.project_name = self.title
		project.expected_start_date = self.start_date
		project.expected_end_date = frappe.utils.data.add_days(self.start_date, period-1)
		project.insert()
		self.create_task(crop_tasks, project.as_dict.im_self.name, self.start_date)
		return project.as_dict.im_self.name

	def create_task(self, crop_tasks, project_name, start_date):
		for crop_task in crop_tasks:
			print crop_task
			task = frappe.new_doc("Task")
			task.subject = crop_task.get("subject")
			task.priority = crop_task.get("priority")
			task.project = project_name
			task.exp_start_date = frappe.utils.data.add_days(start_date, crop_task.get("start_day")-1)
			task.exp_end_date = frappe.utils.data.add_days(start_date, crop_task.get("end_day")-1)
			task.insert()