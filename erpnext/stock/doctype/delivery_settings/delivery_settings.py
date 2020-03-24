# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.model.document import Document

class DeliverySettings(Document):
	
	def validate(self):
		self.validate_delivery_window_times()

	def validate_delivery_window_times(self):
		if self.delivery_start_time and self.delivery_end_time:
			if self.delivery_start_time > self.delivery_end_time:
				return frappe.throw(_('Delivery start window should be before closing window'))
