# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class QualityFeedback(Document):

	def get_quality_feedback_template(self, template):
		doc = frappe.get_doc("Quality Feedback Template", template)

		for parameter in doc.parameters:
			self.append("parameters",
				{
					"parameter": parameter.parameter
				}
			)