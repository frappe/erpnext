# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.nestedset import NestedSet, get_root_of


class SupplierGroup(NestedSet):
	nsm_parent_field = "parent_supplier_group"

	def validate(self):
		if not self.parent_supplier_group:
			self.parent_supplier_group = get_root_of("Supplier Group")
<<<<<<< HEAD
=======
		self.validate_currency_for_payable_and_advance_account()

	def validate_currency_for_payable_and_advance_account(self):
		for x in self.accounts:
			payable_account_currency = None
			advance_account_currency = None

			if x.account:
				payable_account_currency = frappe.get_cached_value("Account", x.account, "account_currency")

			if x.advance_account:
				advance_account_currency = frappe.get_cached_value(
					"Account", x.advance_account, "account_currency"
				)

			if (
				payable_account_currency
				and advance_account_currency
				and payable_account_currency != advance_account_currency
			):
				frappe.throw(
					_(
						"Both Payable Account: {0} and Advance Account: {1} must be of same currency for company: {2}"
					).format(
						frappe.bold(x.account),
						frappe.bold(x.advance_account),
						frappe.bold(x.company),
					)
				)
>>>>>>> 164498bafb (refactor: allow foreign currency accounts in Supplier Group)

	def on_update(self):
		NestedSet.on_update(self)
		self.validate_one_root()

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)
