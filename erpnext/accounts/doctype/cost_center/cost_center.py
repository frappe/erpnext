# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import msgprint, _

from frappe.utils.nestedset import NestedSet

class CostCenter(NestedSet):
	nsm_parent_field = 'parent_cost_center'

	def autoname(self):
		self.name = self.cost_center_name.strip() + ' - ' + \
			frappe.db.get_value("Company", self.company, "abbr")

	def validate_mandatory(self):
		if not self.group_or_ledger:
			msgprint(_("Please select Group or Ledger value"), raise_exception=1)

		if self.cost_center_name != self.company and not self.parent_cost_center:
			msgprint(_("Please enter parent cost center"), raise_exception=1)
		elif self.cost_center_name == self.company and self.parent_cost_center:
			msgprint(_("Root cannot have a parent cost center"), raise_exception=1)

	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			msgprint(_("Cannot convert Cost Center to ledger as it has child nodes"), raise_exception=1)
		elif self.check_gle_exists():
			msgprint(_("Cost Center with existing transactions can not be converted to ledger"), raise_exception=1)
		else:
			self.group_or_ledger = 'Ledger'
			self.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			msgprint(_("Cost Center with existing transactions can not be converted to group"), raise_exception=1)
		else:
			self.group_or_ledger = 'Group'
			self.save()
			return 1

	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"cost_center": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql("select name from `tabCost Center` where \
			parent_cost_center = %s and docstatus != 2", self.name)

	def validate_budget_details(self):
		check_acc_list = []
		for d in self.get('budgets'):
			if self.group_or_ledger=="Group":
				msgprint(_("Budget cannot be set for Group Cost Centers"), raise_exception=1)

			if [d.account, d.fiscal_year] in check_acc_list:
				msgprint(_("Account {0} has been entered more than once for fiscal year {1}").format(d.account, d.fiscal_year), raise_exception=1)
			else:
				check_acc_list.append([d.account, d.fiscal_year])

	def validate(self):
		self.validate_mandatory()
		self.validate_budget_details()

	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_cost_center = get_name_with_abbr(newdn, self.company)

		# Validate properties before merging
		super(CostCenter, self).before_rename(olddn, new_cost_center, merge, "group_or_ledger")

		return new_cost_center

	def after_rename(self, olddn, newdn, merge=False):
		if not merge:
			frappe.db.set_value("Cost Center", newdn, "cost_center_name",
				" - ".join(newdn.split(" - ")[:-1]))
		else:
			super(CostCenter, self).after_rename(olddn, newdn, merge)

