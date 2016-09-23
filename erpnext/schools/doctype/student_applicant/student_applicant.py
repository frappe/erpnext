# -*- coding: utf-8 -*-777777yyy
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class StudentApplicant(Document):
	def validate(self):
		self.title = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))

	def on_update_after_submit(self):
		student = frappe.get_list("Student",  filters= {"student_applicant": self.name})
		if student:
			frappe.throw(_("Cannot change status as student {0} is linked with student application {1}").format(student[0].name, self.name))

	def on_payment_authorized(self, *args, **kwargs):
		self.db_set('paid', 1)