# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TherapyPlan(Document):
	def validate(self):
		self.set_totals()
		self.set_status()

	def set_status(self):
		if not self.total_sessions_completed:
			self.status = 'Not Started'
		else:
			if self.total_sessions_completed < self.total_sessions:
				self.status = 'In Progress'
			elif self.total_sessions_completed == self.total_sessions:
				self.status = 'Completed'

	def set_totals(self):
		total_sessions = sum([int(d.no_of_sessions) for d in self.get('therapy_plan_details')])
		total_sessions_completed = sum([int(d.sessions_completed) for d in self.get('therapy_plan_details')])
		self.db_set('total_sessions', total_sessions)
		self.db_set('total_sessions_completed', total_sessions_completed)


@frappe.whitelist()
def make_therapy_session(therapy_plan, patient, therapy_type):
	therapy_type = frappe.get_doc('Therapy Type', therapy_type)

	therapy_session = frappe.new_doc('Therapy Session')
	therapy_session.therapy_plan = therapy_plan
	therapy_session.patient = patient
	therapy_session.therapy_type = therapy_type.name
	therapy_session.duration = therapy_type.default_duration
	therapy_session.rate = therapy_type.rate
	therapy_session.exercises = therapy_type.exercises

	return therapy_session.as_dict()