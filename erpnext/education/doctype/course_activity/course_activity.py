# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class CourseActivity(Document):
	def validate(self):
		self.check_if_enrolled()

	def check_if_enrolled(self):
		if frappe.db.exists("Course Enrollment", self.enrollment):
			return True
		else:
			frappe.throw(_("Course Enrollment {0} does not exists").format(self.enrollment))
