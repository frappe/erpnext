# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import ast

class CropCycle(Document):
	def validate(self):
		if self.is_new():
			crop = frappe.get_doc('Crop', self.crop)
			self.create_project(crop.period, crop.agriculture_task)
			if not self.crop_spacing_uom:
				self.crop_spacing_uom = crop.crop_spacing_uom
			if not self.row_spacing_uom:
				self.row_spacing_uom = crop.row_spacing_uom
			if not self.project:
				self.project = self.name
			disease = []
			for detected_disease in self.detected_disease:
				disease.append(detected_disease.name)
			if disease != []:
				self.update_disease(disease)
		else:
			old_disease, new_disease = [], []
			for detected_disease in self.detected_disease:
				new_disease.append(detected_disease.name)
			for detected_disease in self.get_doc_before_save().get('detected_disease'):
				old_disease.append(detected_disease.name)
			if list(set(new_disease)-set(old_disease)) != []:
				self.update_disease(list(set(new_disease)-set(old_disease)))
				frappe.msgprint("All tasks for the detected diseases were imported")

	def update_disease(self, disease_hashes):
		new_disease = []
		for disease in self.detected_disease:
			for disease_hash in disease_hashes:
				if disease.name == disease_hash:
					self.import_disease_tasks(disease.disease, disease.start_date)

	def import_disease_tasks(self, disease, start_date):
		disease_doc = frappe.get_doc('Disease', disease)
		self.create_task(disease_doc.treatment_task, self.name, start_date)

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
			task = frappe.new_doc("Task")
			task.subject = crop_task.get("task_name")
			task.priority = crop_task.get("priority")
			task.project = project_name
			task.exp_start_date = frappe.utils.data.add_days(start_date, crop_task.get("start_day")-1)
			task.exp_end_date = frappe.utils.data.add_days(start_date, crop_task.get("end_day")-1)
			task.insert()

	def reload_linked_analysis(self):
		linked_doctypes = ['Soil Texture', 'Soil Analysis', 'Plant Analysis']
		required_fields = ['location', 'name', 'collection_datetime']
		output = {}
		for doctype in linked_doctypes:
			output[doctype] = frappe.get_all(doctype, fields=required_fields)
		output['Land Unit'] = []
		for land in self.linked_land_unit:
			output['Land Unit'].append(frappe.get_doc('Land Unit', land.land_unit))

		frappe.publish_realtime("List of Linked Docs", output, user=frappe.session.user)

	def append_to_child(self, obj_to_append):
		for doctype in obj_to_append:
			for doc_name in set(obj_to_append[doctype]):
				self.append(doctype, {doctype: doc_name})
		self.save()

	def get_coordinates(self, doc):
		return ast.literal_eval(doc.location).get('features')[0].get('geometry').get('coordinates')

	def get_geometry_type(self, doc):
		return ast.literal_eval(doc.location).get('features')[0].get('geometry').get('type')

	def is_in_land_unit(self, point, vs):
		x, y = point
		inside = False
		j = len(vs)-1
		i = 0
		while i < len(vs):
			xi, yi = vs[i]
			xj, yj = vs[j]
			intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
			if intersect:
				inside = not inside
			i = j
			j += 1
		return inside