# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt


class AuthorizationRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approving_role: DF.Link | None
		approving_user: DF.Link | None
		based_on: DF.Literal[
			"",
			"Grand Total",
			"Average Discount",
			"Customerwise Discount",
			"Itemwise Discount",
			"Item Group wise Discount",
			"Not Applicable",
		]
		company: DF.Link | None
		customer_or_item: DF.Literal["Customer", "Item", "Item Group"]
		master_name: DF.DynamicLink | None
		system_role: DF.Link | None
		system_user: DF.Link | None
		to_designation: DF.Link | None
		to_emp: DF.Link | None
		transaction: DF.Literal[
			"",
			"Sales Order",
			"Purchase Order",
			"Quotation",
			"Delivery Note",
			"Sales Invoice",
			"Purchase Invoice",
			"Purchase Receipt",
		]
		value: DF.Float
	# end: auto-generated types

	def check_duplicate_entry(self):
		exists = frappe.db.sql(
			"""select name, docstatus from `tabAuthorization Rule`
			where transaction = %s and based_on = %s and system_user = %s
			and system_role = %s and approving_user = %s and approving_role = %s
			and to_emp =%s and to_designation=%s and name != %s""",
			(
				self.transaction,
				self.based_on,
				cstr(self.system_user),
				cstr(self.system_role),
				cstr(self.approving_user),
				cstr(self.approving_role),
				cstr(self.to_emp),
				cstr(self.to_designation),
				self.name,
			),
		)
		auth_exists = exists and exists[0][0] or ""
		if auth_exists:
			frappe.throw(_("Duplicate Entry. Please check Authorization Rule {0}").format(auth_exists))

	def validate_rule(self):
		if not self.approving_role and not self.approving_user:
			frappe.throw(_("Please enter Approving Role or Approving User"))
		elif self.system_user and self.system_user == self.approving_user:
			frappe.throw(_("Approving User cannot be same as user the rule is Applicable To"))
		elif self.system_role and self.system_role == self.approving_role:
			frappe.throw(_("Approving Role cannot be same as role the rule is Applicable To"))
		elif self.transaction in [
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
			"Stock Entry",
		] and self.based_on in [
			"Average Discount",
			"Customerwise Discount",
			"Itemwise Discount",
			"Item Group wise Discount",
		]:
			frappe.throw(_("Cannot set authorization on basis of Discount for {0}").format(self.transaction))
		elif self.based_on == "Average Discount" and flt(self.value) > 100.00:
			frappe.throw(_("Discount must be less than 100"))
		elif self.based_on == "Customerwise Discount" and not self.master_name:
			frappe.throw(_("Customer required for 'Customerwise Discount'"))

	def validate(self):
		self.check_duplicate_entry()
		self.validate_rule()
		if not self.value:
			self.value = 0.0
