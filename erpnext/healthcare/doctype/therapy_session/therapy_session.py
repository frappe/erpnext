# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class TherapySession(Document):
	def on_submit(self):
		self.update_sessions_count_in_therapy_plan()

	def on_cancel(self):
		self.update_sessions_count_in_therapy_plan(on_cancel=True)

	def update_sessions_count_in_therapy_plan(self, on_cancel=False):
		therapy_plan = frappe.get_doc('Therapy Plan', self.therapy_plan)
		for entry in therapy_plan.therapy_plan_details:
			if entry.therapy_type == self.therapy_type:
				if on_cancel:
					entry.sessions_completed -= 1
				else:
					entry.sessions_completed += 1
		therapy_plan.save()


@frappe.whitelist()
def create_therapy_session(source_name, target_doc=None):
	def set_missing_values(source, target):
		therapy_type = frappe.get_doc('Therapy Type', source.therapy_type)
		target.exercises = therapy_type.exercises

	doc = get_mapped_doc('Patient Appointment', source_name, {
			'Patient Appointment': {
				'doctype': 'Therapy Session',
				'field_map': [
					['appointment', 'name'],
					['patient', 'patient'],
					['patient_age', 'patient_age'],
					['gender', 'patient_sex'],
					['therapy_type', 'therapy_type'],
					['therapy_plan', 'therapy_plan'],
					['practitioner', 'practitioner'],
					['department', 'department'],
					['start_date', 'appointment_date'],
					['start_time', 'appointment_time'],
					['service_unit', 'service_unit'],
					['company', 'company'],
					['invoiced', 'invoiced']
				]
			}
		}, target_doc, set_missing_values)

	return doc