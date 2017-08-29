# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.model.document import Document

school_keydict = {
	# "key in defaults": "key in Global Defaults"
	"academic_year": "current_academic_year",
	"academic_term": "current_academic_term",
	"validate_batch": "validate_batch",
	"validate_course": "validate_course"
}

class SchoolSettings(Document):
	def on_update(self):
		"""update defaults"""
		for key in school_keydict:
			frappe.db.set_default(key, self.get(school_keydict[key], ''))

		# clear cache
		frappe.clear_cache()

	def get_defaults(self):
		return frappe.defaults.get_defaults()

	def validate(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter
		if self.get('instructor_created_by')=='Naming Series':
			make_property_setter('Instructor', "naming_series", "hidden", 0, "Check")
		else:
			make_property_setter('Instructor', "naming_series", "hidden", 1, "Check")
