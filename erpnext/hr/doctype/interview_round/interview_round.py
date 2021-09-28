# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class InterviewRound(Document):
	pass

@frappe.whitelist()
def create_interview(doc):
	import json
	from six import string_types

	if isinstance(doc, string_types):
		doc = json.loads(doc)

	if doc:
		doc = frappe.get_doc(doc)

		interview = frappe.new_doc("Interview")
		interview.interview_round = doc.name
		interview.designation = doc.designation

		if doc.interviewer:
			interview.interview_detail = []
			for data in doc.interviewer:
				interview.append("interview_detail", {
						"interviewer": data.user
					})
		return interview



