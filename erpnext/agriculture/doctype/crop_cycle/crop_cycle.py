# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CropCycle(Document):
	def autoname(self):
		if self.site_name == None:
			return self.name = '{crop} {start_date} {end_date}'.formate(crop = self.crop, start_date = self.start_date, end_date = self.end_date)