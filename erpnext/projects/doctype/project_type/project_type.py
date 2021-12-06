# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ProjectType(Document):
	def on_trash(self):
		if self.name == "External":
			frappe.throw(_("You cannot delete Project Type 'External'"))
