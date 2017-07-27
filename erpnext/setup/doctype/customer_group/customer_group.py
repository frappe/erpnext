# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


from frappe.utils.nestedset import NestedSet
class CustomerGroup(NestedSet):
	nsm_parent_field = 'parent_customer_group';

	def on_update(self):
		self.validate_name_with_customer()
		super(CustomerGroup, self).on_update()
		self.validate_one_root()

	def validate_name_with_customer(self):
		if frappe.db.exists("Customer", self.name):
			frappe.msgprint(_("An Customer exists with same name"), raise_exception=1)
