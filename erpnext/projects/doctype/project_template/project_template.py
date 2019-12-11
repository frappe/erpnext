# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.support.doctype.service_level.service_level import get_repeated

class ProjectTemplate(Document):

	def validate(self):
		skip_weekdays = self.get_skip_weekdays()

		if not len(set(skip_weekdays)) == len(skip_weekdays):
			repeated_days = get_repeated(skip_weekdays)
			frappe.throw(_("Day {0} has been repeated.".format(repeated_days)))

	def get_skip_weekdays(self):
		return [day.day for day in self.skip_weekdays]