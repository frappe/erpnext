# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class HotelRoom(Document):
	def validate(self):
		if not self.capacity:
			self.capacity, self.extra_bed_capacity = frappe.db.get_value(
				"Hotel Room Type", self.hotel_room_type, ["capacity", "extra_bed_capacity"]
			)
