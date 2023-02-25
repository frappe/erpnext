# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

from erpnext.accounts.utils import validate_field_number


class CostCenter(NestedSet):
	nsm_parent_field = "parent_cost_center"

	def autoname(self):
		from erpnext.accounts.utils import get_autoname_with_number

		self.name = get_autoname_with_number(
			self.cost_center_number, self.cost_center_name, self.company
		)

	def validate(self):
		self.validate_mandatory()
		self.validate_parent_cost_center()

	def validate_mandatory(self):
		if self.cost_center_name != self.company and not self.parent_cost_center:
			frappe.throw(_("Please enter parent cost center"))
		elif self.cost_center_name == self.company and self.parent_cost_center:
			frappe.throw(_("Root cannot have a parent cost center"))

	def validate_parent_cost_center(self):
		if self.parent_cost_center:
			if not frappe.db.get_value("Cost Center", self.parent_cost_center, "is_group"):
				frappe.throw(
					_("{0} is not a group node. Please select a group node as parent cost center").format(
						frappe.bold(self.parent_cost_center)
					)
				)

	@frappe.whitelist()
	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			frappe.throw(_("Cannot convert Cost Center to ledger as it has child nodes"))
		elif self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to ledger"))
		else:
			self.is_group = 0
			self.save()
			return 1

	@frappe.whitelist()
	def convert_ledger_to_group(self):
		if self.if_allocation_exists_against_cost_center():
			frappe.throw(_("Cost Center with Allocation records can not be converted to a group"))
		if self.check_if_part_of_cost_center_allocation():
			frappe.throw(
				_("Cost Center is a part of Cost Center Allocation, hence cannot be converted to a group")
			)
		if self.check_gle_exists():
			frappe.throw(_("Cost Center with existing transactions can not be converted to group"))
		self.is_group = 1
		self.save()
		return 1

	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"cost_center": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql(
			"select name from `tabCost Center` where \
			parent_cost_center = %s and docstatus != 2",
			self.name,
		)

	def if_allocation_exists_against_cost_center(self):
		return frappe.db.get_value(
			"Cost Center Allocation", filters={"main_cost_center": self.name, "docstatus": 1}
		)

	def check_if_part_of_cost_center_allocation(self):
		return frappe.db.get_value(
			"Cost Center Allocation Percentage", filters={"cost_center": self.name, "docstatus": 1}
		)

	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr

		new_cost_center = get_name_with_abbr(newdn, self.company)

		# Validate properties before merging
		super(CostCenter, self).before_rename(olddn, new_cost_center, merge, "is_group")
		if not merge:
			new_cost_center = get_name_with_number(new_cost_center, self.cost_center_number)

		return new_cost_center

	def after_rename(self, olddn, newdn, merge=False):
		super(CostCenter, self).after_rename(olddn, newdn, merge)

		if not merge:
			new_cost_center = frappe.db.get_value(
				"Cost Center", newdn, ["cost_center_name", "cost_center_number"], as_dict=1
			)

			# exclude company abbr
			new_parts = newdn.split(" - ")[:-1]
			# update cost center number and remove from parts
			if new_parts[0][0].isdigit():
				if len(new_parts) == 1:
					new_parts = newdn.split(" ")
				if new_cost_center.cost_center_number != new_parts[0]:
					validate_field_number(
						"Cost Center", self.name, new_parts[0], self.company, "cost_center_number"
					)
					self.cost_center_number = new_parts[0]
					self.db_set("cost_center_number", new_parts[0])
				new_parts = new_parts[1:]

			# update cost center name
			cost_center_name = " - ".join(new_parts)
			if new_cost_center.cost_center_name != cost_center_name:
				self.cost_center_name = cost_center_name
				self.db_set("cost_center_name", cost_center_name)


def on_doctype_update():
	frappe.db.add_index("Cost Center", ["lft", "rgt"])


def get_name_with_number(new_account, account_number):
	if account_number and not new_account[0].isdigit():
		new_account = account_number + " - " + new_account
	return new_account
