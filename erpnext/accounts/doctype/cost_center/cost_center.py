# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cstr

class CostCenter(NestedSet):
	nsm_parent_field = 'parent_cost_center'

	def autoname(self):
		self.name = get_cost_center_autoname(self.cost_center_number, self.cost_center_name, self.company)
			
	def validate(self):
		self.validate_mandatory()
		validate_cost_center_number(self.name, self.cost_center_number, self.company)

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
		new_cost_center = get_name_with_number(newdn, self.cost_center_number)

		# Validate properties before merging
		super(CostCenter, self).before_rename(olddn, new_cost_center, merge, "is_group")

		return new_cost_center

	def after_rename(self, olddn, newdn, merge=False):
		if not merge:
			new_cc = frappe.db.get_value("Cost Center", newdn, ["cost_center_name", "cost_center_number"], as_dict=1)
			# exclude company abbr
			new_parts = newdn.split(" - ")[:-1]

			# update cost center number and remove from parts
			if new_parts[0][0].isdigit():
				# if cost center number is separate by space, split using space
				if len(new_parts) == 1:
					new_parts = newdn.split(" ")
				if new_cc.cost_center_number != new_parts[0]:
					self.cost_center_number = new_parts[0]
					self.db_set("cost_center_number", new_parts[0])
				new_parts = new_parts[1:]

			frappe.db.set_value("Cost Center", newdn, "cost_center_name",
				" - ".join(newdn.split(" - ")[:-1]))
		else:
			super(CostCenter, self).after_rename(olddn, newdn, merge)

def get_cost_center_autoname(cost_center_number, cost_center_name, company):
	company = frappe.db.get_value("Company", company, ["abbr", "name"], as_dict=True)
	if not company:
		frappe.throw(_('Company {0} does not exist').format(company))

	parts = [cost_center_name.strip(), company.abbr]
	if cstr(cost_center_number).strip():
		parts.insert(0, cstr(cost_center_number).strip())
	return ' - '.join(parts)

def validate_cost_center_number(name, cost_center_number, company):
	if cost_center_number:
		cost_center_with_same_number = frappe.db.get_value("Cost Center",
			{"cost_center_number": cost_center_number, "company": company, "name": ["!=", name]})
		if cost_center_with_same_number:
			frappe.throw(_("Cost Center Number {0} already used in cost center {1}")
				.format(cost_center_number, cost_center_with_same_number))

@frappe.whitelist()
def update_cost_center_number(name, cost_center_number):
	cost_center = frappe.db.get_value("Cost Center", name, ["cost_center_name", "company"], as_dict=True)

	validate_cost_center_number(name, cost_center_number, cost_center.company)

	frappe.db.set_value("Cost Center", name, "cost_center_number", cost_center_number)

	cost_center_name = cost_center.cost_center_name
	if cost_center_name[0].isdigit():
		separator = " - " if " - " in cost_center_name else " "
		cost_center_name = cost_center_name.split(separator, 1)[1]
	frappe.db.set_value("Cost Center", name, "cost_center_name", cost_center_name)

	new_name = get_cost_center_autoname(cost_center_number, cost_center_name, cost_center.company)
	if name != new_name:
		frappe.rename_doc("Cost Center", name, new_name)
		return new_name

def get_name_with_number(new_cost_center, cost_center_number):
	if cost_center_number and not new_cost_center[0].isdigit():
		new_cost_center = cost_center_number + " - " + new_cost_center
	return new_cost_center