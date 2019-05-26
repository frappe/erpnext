# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class QualityAction(Document):

	def get_document(self, document_type, document_name):
		doc = frappe.get_doc(document_type, document_name)
		if document_type == "Quality Review":
			resolutions = [review.objective for review in doc.reviews]
		else:
			resolutions = None

		for idx in range(0, len(resolutions)):
			self.append("resolutions",
				{
					"problem": descriptions[idx]
				}
			)
