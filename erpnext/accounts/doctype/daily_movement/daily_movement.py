# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DailyMovement(Document):

	def before_insert(self):
		self.description = self.target_date
		self.description += ' ' + self.payment_mode
