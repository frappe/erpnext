# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LaboratorySettings(Document):
	def validate(self):
		for key in ["require_test_result_approval","require_sample_collection"]:
			frappe.db.set_default(key, self.get(key, ""))
