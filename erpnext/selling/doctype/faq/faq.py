# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class FAQ(Document):
	def autoname(self):
		pass
		# self.name =make_autoname("FAQ"+self.question)
		# self.name=
