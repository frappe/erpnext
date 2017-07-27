# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document
from frappe.model.naming import make_autoname

class Campaign(Document):
	def autoname(self):
		if frappe.defaults.get_global_default('campaign_naming_by') != 'Naming Series':
			self.name = self.campaign_name
		else:
			self.name = make_autoname(self.naming_series+'.#####')
