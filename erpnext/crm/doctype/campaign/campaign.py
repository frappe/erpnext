# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Campaign(Document):
	def autoname(self):
		if frappe.defaults.get_global_default('campaign_naming_by') != 'Naming Series':
			self.name = self.campaign_name
		else:
			set_name_by_naming_series(self)
