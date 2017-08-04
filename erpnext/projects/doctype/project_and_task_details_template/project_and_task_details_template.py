# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe.utils.jinja import validate_template

class ProjectandTaskDetailsTemplate(Document):
	def validate(self):
		if self.details:
			validate_template(self.details)

@frappe.whitelist()
def get_details(template_name, doc):
	if isinstance(doc, basestring):
		doc = json.loads(doc)

	details = frappe.get_doc("Project and Task Details Template", template_name)
	if details.details:
		return frappe.render_template(details.details, doc)
