# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

class CostCenter(NestedSet):
	nsm_parent_field = 'parent_cost_center'

	def autoname(self):
		self.name = self.cost_center_name.strip() + ' - ' + \
			frappe.db.get_value("Company", self.company, "abbr")
			

	def validate(self):
		self.validate_mandatory()

	def validate_mandatory(self):
		if self.cost_center_name != self.company and not self.parent_cost_center:
			frappe.throw(_("Please enter parent cost center"))
		elif self.cost_center_name == self.company and self.parent_cost_center:
			frappe.throw(_("Root cannot have a parent cost center"))

	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			frappe.throw(_("Cannot convert Cost Center to ledger as it has child nodes"))
		elif self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to ledger"))
		else:
			self.is_group = 0
			self.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to group"))
		else:
			self.is_group = 1
			self.save()
			return 1

	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"cost_center": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql("select name from `tabCost Center` where \
			parent_cost_center = %s and docstatus != 2", self.name)

	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_cost_center = get_name_with_abbr(newdn, self.company)

		# Validate properties before merging
		super(CostCenter, self).before_rename(olddn, new_cost_center, merge, "is_group")

		return new_cost_center

	def after_rename(self, olddn, newdn, merge=False):
		super(CostCenter, self).after_rename(olddn, newdn, merge)

		if not merge:
			frappe.db.set_value("Cost Center", newdn, "cost_center_name",
				" - ".join(newdn.split(" - ")[:-1]))
