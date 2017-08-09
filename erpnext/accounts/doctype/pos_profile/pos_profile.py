# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import cint
from erpnext.accounts.doctype.sales_invoice.sales_invoice import set_account_for_mode_of_payment

from frappe.model.document import Document

class POSProfile(Document):
	def validate(self):
		self.check_for_duplicate()
		self.validate_all_link_fields()
		self.validate_duplicate_groups()
		self.check_default_payment()
		self.validate_customer_territory_group()

	def check_for_duplicate(self):
		res = frappe.db.sql("""select name, user from `tabPOS Profile`
			where ifnull(user, '') = %s and name != %s and company = %s""",
			(self.user, self.name, self.company))
		if res:
			if res[0][1]:
				msgprint(_("POS Profile {0} already created for user: {1} and company {2}").format(res[0][0],
					res[0][1], self.company), raise_exception=1)
			else:
				msgprint(_("Global POS Profile {0} already created for company {1}").format(res[0][0],
					self.company), raise_exception=1)

	def validate_all_link_fields(self):
		accounts = {"Account": [self.income_account,
			self.expense_account], "Cost Center": [self.cost_center],
			"Warehouse": [self.warehouse]}

		for link_dt, dn_list in accounts.items():
			for link_dn in dn_list:
				if link_dn and not frappe.db.exists({"doctype": link_dt,
						"company": self.company, "name": link_dn}):
					frappe.throw(_("{0} does not belong to Company {1}").format(link_dn, self.company))

	def validate_duplicate_groups(self):
		item_groups = [d.item_group for d in self.item_groups]
		customer_groups = [d.customer_group for d in self.customer_groups]

		if len(item_groups) != len(set(item_groups)):
			frappe.throw(_("Duplicate item group found in the item group table"), title = "Duplicate Item Group")

		if len(customer_groups) != len(set(customer_groups)):
			frappe.throw(_("Duplicate customer group found in the cutomer group table"), title = "Duplicate Customer Group")

	def check_default_payment(self):
		if self.payments:
			default_mode_of_payment = [d.default for d in self.payments if d.default]
			if not default_mode_of_payment:
				frappe.throw(_("Set default mode of payment"))

			if len(default_mode_of_payment) > 1:
				frappe.throw(_("Multiple default mode of payment is not allowed"))
	def validate_customer_territory_group(self):
		if not self.territory:
			frappe.throw(_("Territory is Required in POS Profile"), title="Mandatory Field")

		if not self.customer_group:
			frappe.throw(_("Customer Group is Required in POS Profile"), title="Mandatory Field")

	def before_save(self):
		set_account_for_mode_of_payment(self)

	def on_update(self):
		self.set_defaults()

	def on_trash(self):
		self.set_defaults(include_current_pos=False)

	def set_defaults(self, include_current_pos=True):
		frappe.defaults.clear_default("is_pos")

		if not include_current_pos:
			condition = " where name != '%s'" % self.name.replace("'", "\'")
		else:
			condition = ""

		pos_view_users = frappe.db.sql_list("""select user
			from `tabPOS Profile` {0}""".format(condition))

		for user in pos_view_users:
			if user:
				frappe.defaults.set_user_default("is_pos", 1, user)
			else:
				frappe.defaults.set_global_default("is_pos", 1)

@frappe.whitelist()
def get_series():
	return frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
