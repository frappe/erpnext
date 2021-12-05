# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

class ExitInterview(Document):
	def validate(self):
		self.validate_relieving_date()

	def validate_relieving_date(self):
		if not frappe.db.get_value('Employee', self.employee, 'relieving_date'):
			frappe.throw(_('Please set the relieving date for employee {0}').format(
				get_link_to_form('Employee', self.employee)),
				title=_('Relieving Date Missing'))
