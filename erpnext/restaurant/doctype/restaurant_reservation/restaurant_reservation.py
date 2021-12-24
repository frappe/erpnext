# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from datetime import timedelta

from frappe.model.document import Document
from frappe.utils import get_datetime


class RestaurantReservation(Document):
	def validate(self):
		if not self.reservation_end_time:
			self.reservation_end_time = get_datetime(self.reservation_time) + timedelta(hours=1)
