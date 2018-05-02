# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe import _

class WaterAnalysis(Document):
	def load_contents(self):
		docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Water Analysis'})
		for doc in docs:
			self.append('water_analysis_criteria', {'title': str(doc.name)})

	def update_lab_result_date(self):
		if not self.result_datetime:
			self.result_datetime = self.laboratory_testing_datetime

	def validate(self):
		if self.collection_datetime > self.laboratory_testing_datetime:
			frappe.throw(_('Lab testing datetime cannot be before collection datetime'))
		if self.laboratory_testing_datetime > self.result_datetime:
			frappe.throw(_('Lab result datetime cannot be before testing datetime'))