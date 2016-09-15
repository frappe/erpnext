# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe import _

class StudentAdmission(WebsiteGenerator):
	website = frappe._dict(
		template = "templates/generators/student_admission.html",
		condition_field = "publish",
		page_title_field = "route"
	)

	def get_context(self, context):
		context.parents = [{'name': 'admissions', 'title': _('All Student Admissions') }]

def get_list_context(context):
	context.title = _("Student Admissions")
