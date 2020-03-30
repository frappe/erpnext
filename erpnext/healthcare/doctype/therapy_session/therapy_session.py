# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TherapySession(Document):
	def on_submit(self):
		self.update_sessions_count_in_therapy_plan()

	def update_sessions_count_in_therapy_plan(self):
		therapy_plan = frappe.get_doc('Therapy Plan', self.therapy_plan)
		for entry in therapy_plan.therapy_plan_details:
			if entry.therapy_type == self.therapy_type:
				entry.sessions_completed += 1
		therapy_plan.save()
