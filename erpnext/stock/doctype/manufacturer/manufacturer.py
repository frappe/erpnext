# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
import frappe


class Manufacturer(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
	
	def after_rename(self, old_name, new_name, merge):
		frappe.db.sql(
			"""
			update
				tabItem
			set
				default_item_manufacturer = %s
			where
				default_item_manufacturer = %s
			""",
			(new_name, old_name)
		)
