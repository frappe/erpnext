# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class City(Document):
	def validate(self):
		if self.location == "External":
			if not self.world_countries:
				frappe.throw("Select Country")
