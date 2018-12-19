# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ServiceLevel(Document):

	def validate(self):
		week = ["Monday",  "Tuesday",  "Wednesday",  "Thursday", "Friday", "Saturday", "Sunday"]
		indexes = [week.index(support_and_resolution.workday) for support_and_resolution in self.support_and_resolution]
		if not len(set(indexes)) == len(indexes):
			frappe.throw(_("Workday has been repeated twice"))
		for support_and_resolution in self.support_and_resolution:
			support_and_resolution.idx = week.index(support_and_resolution.workday) + 1
