# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class Campaign(Document):
	def autoname(self):
		if frappe.defaults.get_global_default('campaign_naming_by') == 'Campaign Name':
			self.name = self.campaign_name
		else:
			self.name = make_autoname(self.naming_series+'.#####')
