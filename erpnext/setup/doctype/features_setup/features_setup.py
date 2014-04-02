# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class FeaturesSetup(Document):

	def validate(self):
		"""
			update settings in defaults
		"""
		from frappe.model import default_fields 
		from frappe.utils import set_default
		for key in self.meta.get_valid_columns():
			if key not in default_fields:
				set_default(key, self.get(key))
