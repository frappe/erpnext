# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint, scrub, unscrub
from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
from frappe.model.document import Document
from frappe.utils import get_link_to_form, now

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)


class POSProfile(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pos_customer_group.pos_customer_group import POSCustomerGroup
		from erpnext.accounts.doctype.pos_item_group.pos_item_group import POSItemGroup
		from erpnext.accounts.doctype.pos_payment_method.pos_payment_method import POSPaymentMethod
		from erpnext.accounts.doctype.pos_profile_user.pos_profile_user import POSProfileUser

		account_for_change_amount: DF.Link | None
		action_on_new_invoice: DF.Literal[
			"Always Ask", "Save Changes and Load New Invoice", "Discard Changes and Load New Invoice"
		]
		allow_discount_change: DF.Check
		allow_partial_payment: DF.Check
		allow_rate_change: DF.Check
		applicable_for_users: DF.Table[POSProfileUser]
		apply_discount_on: DF.Literal["Grand Total", "Net Total"]
		auto_add_item_to_cart: DF.Check
		company: DF.Link
		company_address: DF.Link | None
		cost_center: DF.Link | None
		country: DF.ReadOnly | None
		currency: DF.Link
		customer: DF.Link | None
		customer_groups: DF.Table[POSCustomerGroup]
		disable_rounded_total: DF.Check
		disabled: DF.Check
		expense_account: DF.Link | None
		hide_images: DF.Check
		hide_unavailable_items: DF.Check
		ignore_pricing_rule: DF.Check
		income_account: DF.Link | None
		item_groups: DF.Table[POSItemGroup]
		letter_head: DF.Link | None
		payments: DF.Table[POSPaymentMethod]
		print_format: DF.Link | None
		print_receipt_on_order_complete: DF.Check
		project: DF.Link | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link | None
		set_grand_total_to_default_mop: DF.Check
		tax_category: DF.Link | None
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		update_stock: DF.Check
		utm_campaign: DF.Link | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		validate_stock_on_save: DF.Check
		warehouse: DF.Link
		write_off_account: DF.Link
		write_off_cost_center: DF.Link
		write_off_limit: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_disabled()
		self.validate_default_profile()
		self.validate_all_link_fields()
		self.validate_duplicate_groups()
		self.validate_payment_methods()
		self.validate_accounting_dimensions()

	def validate_accounting_dimensions(self):
		acc_dims = get_checks_for_pl_and_bs_accounts()
		for acc_dim in acc_dims:
			if (
				self.company == acc_dim.company
				and not self.get(acc_dim.fieldname)
				and (acc_dim.mandatory_for_pl or acc_dim.mandatory_for_bs)
			):
				frappe.throw(
					_(
						"{0} is a mandatory Accounting Dimension. <br>"
						"Please set a value for {0} in Accounting Dimensions section."
					).format(
						frappe.bold(acc_dim.label),
					),
					title=_("Mandatory Accounting Dimension"),
				)

	def validate_disabled(self):
		old_doc = self.get_doc_before_save()

		if (
			old_doc
			and self.disabled
			and old_doc.disabled != self.disabled
			and frappe.db.exists("POS Opening Entry", {"pos_profile": self.name, "status": "Open"})
		):
			frappe.throw(
				_("POS Profile {0} cannot be disabled as there are ongoing POS sessions.").format(
					frappe.bold(self.name)
				)
			)

	def validate_default_profile(self):
		for row in self.applicable_for_users:
			res = frappe.db.sql(
				"""select pf.name
				from
					`tabPOS Profile User` pfu, `tabPOS Profile` pf
				where
					pf.name = pfu.parent and pfu.user = %s and pf.name != %s and pf.company = %s
					and pfu.default=1 and pf.disabled = 0""",
				(row.user, self.name, self.company),
			)

			if row.default and res:
				msgprint(
					_("Already set default in pos profile {0} for user {1}, kindly disabled default").format(
						res[0][0], row.user
					),
					raise_exception=1,
				)
			elif not row.default and not res:
				msgprint(
					_(
						"User {0} doesn't have any default POS Profile. Check Default at Row {1} for this User."
					).format(row.user, row.idx)
				)

	def validate_all_link_fields(self):
		accounts = {
			"Account": [self.income_account, self.expense_account],
			"Cost Center": [self.cost_center],
			"Warehouse": [self.warehouse],
		}

		for link_dt, dn_list in accounts.items():
			for link_dn in dn_list:
				if link_dn and not frappe.db.exists(
					{"doctype": link_dt, "company": self.company, "name": link_dn}
				):
					frappe.throw(_("{0} does not belong to Company {1}").format(link_dn, self.company))

	def validate_duplicate_groups(self):
		item_groups = [d.item_group for d in self.item_groups]
		customer_groups = [d.customer_group for d in self.customer_groups]

		if len(item_groups) != len(set(item_groups)):
			frappe.throw(
				_("Duplicate item group found in the item group table"), title=_("Duplicate Item Group")
			)

		if len(customer_groups) != len(set(customer_groups)):
			frappe.throw(
				_("Duplicate customer group found in the customer group table"),
				title=_("Duplicate Customer Group"),
			)

	def validate_payment_methods(self):
		if not self.payments:
			frappe.throw(_("Payment methods are mandatory. Please add at least one payment method."))

		default_mode = [d.default for d in self.payments if d.default]
		if not default_mode:
			frappe.throw(_("Please select a default mode of payment"))

		if len(default_mode) > 1:
			frappe.throw(_("You can only select one mode of payment as default"))

		invalid_modes = []
		for d in self.payments:
			account = frappe.db.get_value(
				"Mode of Payment Account",
				{"parent": d.mode_of_payment, "company": self.company},
				"default_account",
			)

			if not account:
				invalid_modes.append(get_link_to_form("Mode of Payment", d.mode_of_payment))

		if invalid_modes:
			if invalid_modes == 1:
				msg = _("Please set default Cash or Bank account in Mode of Payment {}")
			else:
				msg = _("Please set default Cash or Bank account in Mode of Payments {}")
			frappe.throw(msg.format(", ".join(invalid_modes)), title=_("Missing Account"))

	def on_update(self):
		self.set_defaults()

	def on_trash(self):
		self.set_defaults(include_current_pos=False)

	def set_defaults(self, include_current_pos=True):
		frappe.defaults.clear_default("is_pos")

		if not include_current_pos:
			condition = " where pfu.name != '%s' and pfu.default = 1 " % self.name.replace("'", "'")
		else:
			condition = " where pfu.default = 1 "

		pos_view_users = frappe.db.sql_list(
			f"""select pfu.user
			from `tabPOS Profile User` as pfu {condition}"""
		)

		for user in pos_view_users:
			if user:
				frappe.defaults.set_user_default("is_pos", 1, user)
			else:
				frappe.defaults.set_global_default("is_pos", 1)


def get_item_groups(pos_profile):
	item_groups = []
	pos_profile = frappe.get_cached_doc("POS Profile", pos_profile)
	permitted_item_groups = get_permitted_nodes("Item Group")

	if pos_profile.get("item_groups"):
		# Get items based on the item groups defined in the POS profile
		for data in pos_profile.get("item_groups"):
			item_groups.extend(
				[
					"%s" % frappe.db.escape(d.name)
					for d in get_child_nodes("Item Group", data.item_group)
					if not permitted_item_groups or d.name in permitted_item_groups
				]
			)

	if not item_groups and permitted_item_groups:
		item_groups = ["%s" % frappe.db.escape(d) for d in permitted_item_groups]

	return list(set(item_groups))


def get_permitted_nodes(group_type):
	nodes = []
	permitted_nodes = get_permitted_documents(group_type)

	if not permitted_nodes:
		return nodes

	for node in permitted_nodes:
		if frappe.db.get_value(group_type, node, "is_group"):
			nodes.extend([d.name for d in get_child_nodes(group_type, node)])
		else:
			nodes.append(node)

	return nodes


def get_child_nodes(group_type, root):
	lft, rgt = frappe.db.get_value(group_type, root, ["lft", "rgt"])
	return frappe.db.sql(
		f""" Select name, lft, rgt from `tab{group_type}` where
			lft >= {lft} and rgt <= {rgt} order by lft""",
		as_dict=1,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def pos_profile_query(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session["user"]
	company = filters.get("company") or frappe.defaults.get_user_default("company")

	args = {
		"user": user,
		"start": start,
		"company": company,
		"page_len": page_len,
		"txt": "%%%s%%" % txt,
	}

	pos_profile = frappe.db.sql(
		"""select pf.name
		from
			`tabPOS Profile` pf, `tabPOS Profile User` pfu
		where
			pfu.parent = pf.name and pfu.user = %(user)s and pf.company = %(company)s
			and (pf.name like %(txt)s)
			and pf.disabled = 0 limit %(page_len)s offset %(start)s""",
		args,
	)

	if not pos_profile:
		del args["user"]

		pos_profile = frappe.db.sql(
			"""select pf.name
			from
				`tabPOS Profile` pf left join `tabPOS Profile User` pfu
			on
				pf.name = pfu.parent
			where
				ifnull(pfu.user, '') = ''
				and pf.company = %(company)s
				and pf.name like %(txt)s
				and pf.disabled = 0""",
			args,
		)

	return pos_profile


@frappe.whitelist()
def set_default_profile(pos_profile, company):
	modified = now()
	user = frappe.session.user

	if pos_profile and company:
		frappe.db.sql(
			""" update `tabPOS Profile User` pfu, `tabPOS Profile` pf
			set
				pfu.default = 0, pf.modified = %s, pf.modified_by = %s
			where
				pfu.user = %s and pf.name = pfu.parent and pf.company = %s
				and pfu.default = 1""",
			(modified, user, user, company),
			auto_commit=1,
		)

		frappe.db.sql(
			""" update `tabPOS Profile User` pfu, `tabPOS Profile` pf
			set
				pfu.default = 1, pf.modified = %s, pf.modified_by = %s
			where
				pfu.user = %s and pf.name = pfu.parent and pf.company = %s and pf.name = %s
			""",
			(modified, user, user, company, pos_profile),
			auto_commit=1,
		)
