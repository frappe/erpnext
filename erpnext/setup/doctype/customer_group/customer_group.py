# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet, get_root_of


class CustomerGroup(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.party_account.party_account import PartyAccount
		from erpnext.selling.doctype.customer_credit_limit.customer_credit_limit import (
			CustomerCreditLimit,
		)

		accounts: DF.Table[PartyAccount]
		credit_limits: DF.Table[CustomerCreditLimit]
		customer_group_name: DF.Data
		default_price_list: DF.Link | None
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_customer_group: DF.Link | None
		payment_terms: DF.Link | None
		rgt: DF.Int
	# end: auto-generated types

	nsm_parent_field = "parent_customer_group"

	def validate(self):
		if not self.parent_customer_group:
			self.parent_customer_group = get_root_of("Customer Group")
		self.validate_currency_for_receivable_and_advance_account()

	def validate_currency_for_receivable_and_advance_account(self):
		for x in self.accounts:
			company_default_currency = frappe.get_cached_value("Company", x.company, "default_currency")
			receivable_account_currency = None
			advance_account_currency = None

			if x.account:
				receivable_account_currency = frappe.get_cached_value(
					"Account", x.account, "account_currency"
				)

			if x.advance_account:
				advance_account_currency = frappe.get_cached_value(
					"Account", x.advance_account, "account_currency"
				)

			if receivable_account_currency and receivable_account_currency != company_default_currency:
				frappe.throw(
					_("Receivable Account: {0} must be in Company default currency: {1}").format(
						frappe.bold(x.account),
						frappe.bold(company_default_currency),
					)
				)

			if advance_account_currency and advance_account_currency != company_default_currency:
				frappe.throw(
					_("Advance Account: {0} must be in Company default currency: {1}").format(
						frappe.bold(x.advance_account), frappe.bold(company_default_currency)
					)
				)

			if (
				receivable_account_currency
				and advance_account_currency
				and receivable_account_currency != advance_account_currency
			):
				frappe.throw(
					_(
						"Both Receivable Account: {0} and Advance Account: {1} must be of same currency for company: {2}"
					).format(
						frappe.bold(x.account),
						frappe.bold(x.advance_account),
						frappe.bold(x.company),
					)
				)

	def on_update(self):
		self.validate_name_with_customer()
		super().on_update()
		self.validate_one_root()

	def validate_name_with_customer(self):
		if frappe.db.exists("Customer", self.name):
			frappe.msgprint(_("A customer with the same name already exists"), raise_exception=1)


def get_parent_customer_groups(customer_group):
	lft, rgt = frappe.db.get_value("Customer Group", customer_group, ["lft", "rgt"])

	return frappe.db.sql(
		"""select name from `tabCustomer Group`
		where lft <= %s and rgt >= %s
		order by lft asc""",
		(lft, rgt),
		as_dict=True,
	)


def on_doctype_update():
	frappe.db.add_index("Customer Group", ["lft", "rgt"])
