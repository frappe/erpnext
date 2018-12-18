# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ServiceLevel(Document):
	pass	
#	def validate(self):
#		week = ["Monday",  "Tuesday",  "Wednesday",  "Thursday", "Friday", "Saturday", "Sunday"]
#		for count, support_and_resolution in enumerate(self.support_and_resolution):
#			for j in range(0 , len(self.support_and_resolution)-count-1):
#				if week.index(support_and_resolution[j].workday) > week.index(support_and_resolution[j+1].workday):
#					support_and_resolution[j], support_and_resolution[j+1] = support_and_resolution[j+1], support_and_resolution[j]
#		print(self.support_and_resolution)