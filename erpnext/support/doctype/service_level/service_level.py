# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ServiceLevel(Document):

	def validate(self):
		week = ["Monday",  "Tuesday",  "Wednesday",  "Thursday", "Friday", "Saturday", "Sunday"]
		#self.support_and_resolution.sort(key=lambda x: week.index)
		for count, support_and_resolution in enumerate(self.support_and_resolution):
			for support_and_resolution1 in support_and_resolution[:len(self.support_and_resolution)-count-1]:
				if support_and_resolution1.workday > support_and_resolution1:
					pass