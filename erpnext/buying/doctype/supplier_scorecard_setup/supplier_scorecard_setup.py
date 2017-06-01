# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SupplierScorecardSetup(Document):
	
	def validate(self):
		self.validate_standings()

	def validate_standings(self):
		# Check that all possible scores are covered
		pass