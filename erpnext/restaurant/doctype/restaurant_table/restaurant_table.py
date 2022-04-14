# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re

from frappe.model.document import Document
from frappe.model.naming import make_autoname


class RestaurantTable(Document):
	def autoname(self):
		prefix = re.sub("-+", "-", self.restaurant.replace(" ", "-"))
		self.name = make_autoname(prefix + "-.##")
