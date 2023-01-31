# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, get_time_str, time_diff_in_hours


class StockRepostingSettings(Document):
	def validate(self):
		self.set_minimum_reposting_time_slot()

	def set_minimum_reposting_time_slot(self):
		"""Ensure that timeslot for reposting is at least 12 hours."""
		if not self.limit_reposting_timeslot:
			return

		start_time = get_datetime(self.start_time)
		end_time = get_datetime(self.end_time)

		if start_time > end_time:
			end_time = add_to_date(end_time, days=1, as_datetime=True)

		diff = time_diff_in_hours(end_time, start_time)

		if diff < 10:
			self.end_time = get_time_str(add_to_date(self.start_time, hours=10, as_datetime=True))
