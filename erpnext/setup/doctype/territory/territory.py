# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


from frappe.utils import flt
from frappe import _

from frappe.utils.nestedset import NestedSet

class Territory(NestedSet):
	nsm_parent_field = 'parent_territory'

	def validate(self):
		for d in self.get('target_details'):
			if not flt(d.target_qty) and not flt(d.target_amount):
				frappe.throw(_("Either target qty or target amount is mandatory"))

	def on_update(self):
		super(Territory, self).on_update()
		self.validate_one_root()

