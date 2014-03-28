# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.bean import getlist
from frappe import msgprint, _

from frappe.utils.nestedset import DocTypeNestedSet

class CostCenter(DocTypeNestedSet):

		self.nsm_parent_field = 'parent_cost_center'
				
	def autoname(self):
		company_abbr = frappe.db.sql("select abbr from tabCompany where name=%s", 
			self.company)[0][0]
		self.name = self.cost_center_name.strip() + ' - ' + company_abbr
		
	def validate_mandatory(self):
		if not self.group_or_ledger:
			msgprint("Please select Group or Ledger value", raise_exception=1)
			
		if self.cost_center_name != self.company and not self.parent_cost_center:
			msgprint("Please enter parent cost center", raise_exception=1)
		elif self.cost_center_name == self.company and self.parent_cost_center:
			msgprint(_("Root cannot have a parent cost center"), raise_exception=1)
		
	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			msgprint("Cost Center: %s has existing child. You can not convert this cost center to ledger" % (self.name), raise_exception=1)
		elif self.check_gle_exists():
			msgprint("Cost Center with existing transaction can not be converted to ledger.", raise_exception=1)
		else:
			self.group_or_ledger = 'Ledger'
			self.save()
			return 1
			
	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			msgprint("Cost Center with existing transaction can not be converted to group.", raise_exception=1)
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
		for d in self.get('budget_details'):
			if self.group_or_ledger=="Group":
				msgprint("Budget cannot be set for Group Cost Centers", raise_exception=1)
				
			if [d.account, d.fiscal_year] in check_acc_list:
				msgprint("Account " + d.account + "has been entered more than once for fiscal year " + d.fiscal_year, raise_exception=1)
			else: 
				check_acc_list.append([d.account, d.fiscal_year])

	def validate(self):
		"""
			Cost Center name must be unique
		"""
		if (self.get("__islocal") or not self.name) and frappe.db.sql("select name from `tabCost Center` where cost_center_name = %s and company=%s", (self.cost_center_name, self.company)):
			msgprint("Cost Center Name already exists, please rename", raise_exception=1)
			
		self.validate_mandatory()
		self.validate_budget_details()
		
	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_cost_center = get_name_with_abbr(newdn, self.company)
		
		# Validate properties before merging
		super(DocType, self).before_rename(olddn, new_cost_center, merge, "group_or_ledger")
		
		return new_cost_center
		
	def after_rename(self, olddn, newdn, merge=False):
		if not merge:
			frappe.db.set_value("Cost Center", newdn, "cost_center_name", 
				" - ".join(newdn.split(" - ")[:-1]))
		else:
			super(DocType, self).after_rename(olddn, newdn, merge)
			
