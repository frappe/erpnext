# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import timedelta
from frappe.utils import get_datetime

class RestaurantReservation(Document):
	def validate(self):
		if not self.reservation_end_time:
			self.reservation_end_time = get_datetime(self.reservation_time) + timedelta(hours=1)

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Restaurant Reservation", filters)

	data = frappe.db.sql("""select name, reservation_time,
			reservation_end_time, customer_name, status, no_of_people
		from
			`tabRestaurant Reservation`
		where
			((ifnull(reservation_time, '0000-00-00')!= '0000-00-00') \
				and (reservation_time <= %(end)s) \
			or ((ifnull(reservation_end_time, '0000-00-00')!= '0000-00-00') \
				and reservation_end_time >= %(start)s))
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})

	return data
