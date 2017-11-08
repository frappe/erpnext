# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CropCycle(Document):
	def create_tasks(self, subject, day, holiday_management, priority="Low"):
		task = frappe.new_doc("Task")
		task.subject = subject
		task.priority = priority
		task.exp_end_date = frappe.utils.data.add_days(self.start_date, day)
		task.insert()
		frappe.db.commit()
		return task.as_dict.im_self.name