# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import cint, now
from erpnext.accounts.doctype.sales_invoice.pos import get_child_nodes
from erpnext.accounts.doctype.sales_invoice.sales_invoice import set_account_for_mode_of_payment

from frappe.model.document import Document

class POSProfile(Document):
	def validate(self):
		self.validate_default_profile()
		self.validate_all_link_fields()
		self.validate_duplicate_groups()
		self.check_default_payment()
		self.validate_customer_territory_group()

	def validate_default_profile(self):
		for row in self.applicable_for_users:
			res = frappe.db.sql("""select pf.name
				from
					`tabPOS Profile User` pfu, `tabPOS Profile` pf
				where
					pf.name = pfu.parent and pfu.user = %s and pf.name != %s and pf.company = %s
					and pfu.default=1 and pf.disabled = 0""", (row.user, self.name, self.company))

			if row.default and res:
				msgprint(_("Already set default in pos profile {0} for user {1}, kindly disabled default")
					.format(res[0][0], row.user), raise_exception=1)
			elif not row.default and not res:
				msgprint(_("User {0} doesn't have any default POS Profile. Check Default at Row {1} for this User.")
					.format(row.user, row.idx))

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
		if not frappe.db.get_single_value('POS Settings', 'use_pos_in_offline_mode'):
			return

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
			condition = " where pfu.name != '%s' and pfu.default = 1 " % self.name.replace("'", "\'")
		else:
			condition = " where pfu.default = 1 "

		pos_view_users = frappe.db.sql_list("""select pfu.user
			from `tabPOS Profile User` as pfu {0}""".format(condition))

		for user in pos_view_users:
			if user:
				frappe.defaults.set_user_default("is_pos", 1, user)
			else:
				frappe.defaults.set_global_default("is_pos", 1)

def get_item_groups(pos_profile):
	item_groups = []
	pos_profile = frappe.get_doc('POS Profile', pos_profile)

	if pos_profile.get('item_groups'):
		# Get items based on the item groups defined in the POS profile
		for data in pos_profile.get('item_groups'):
			item_groups.extend(["'%s'" % frappe.db.escape(d.name) for d in get_child_nodes('Item Group', data.item_group)])

	return list(set(item_groups))

@frappe.whitelist()
def get_series():
	return frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""

def pos_profile_query(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session['user']
	company = filters.get('company') or frappe.defaults.get_user_default('company')

	args = {
		'user': user,
		'start': start,
		'company': company,
		'page_len': page_len,
		'txt': '%%%s%%' % txt
	}

	pos_profile = frappe.db.sql("""select pf.name, pf.pos_profile_name
		from
			`tabPOS Profile` pf, `tabPOS Profile User` pfu
		where
			pfu.parent = pf.name and pfu.user = %(user)s and pf.company = %(company)s
			and (pf.name like %(txt)s or pf.pos_profile_name like %(txt)s)
			and pf.disabled = 0 limit %(start)s, %(page_len)s""", args)

	if not pos_profile:
		del args['user']

		pos_profile = frappe.db.sql("""select pf.name, pf.pos_profile_name
			from
				`tabPOS Profile` pf left join `tabPOS Profile User` pfu
			on
				pf.name = pfu.parent
			where
				ifnull(pfu.user, '') = '' and pf.company = %(company)s and
				(pf.name like %(txt)s or pf.pos_profile_name like %(txt)s)
				and pf.disabled = 0""", args)

	return pos_profile

@frappe.whitelist()
def set_default_profile(pos_profile, company):
	modified = now()
	user = frappe.session.user
	company = frappe.db.escape(company)

	if pos_profile and company:
		frappe.db.sql(""" update `tabPOS Profile User` pfu, `tabPOS Profile` pf
			set
				pfu.default = 0, pf.modified = %s, pf.modified_by = %s
			where
				pfu.user = %s and pf.name = pfu.parent and pf.company = %s
				and pfu.default = 1""", (modified, user, user, company), auto_commit=1)

		frappe.db.sql(""" update `tabPOS Profile User` pfu, `tabPOS Profile` pf
			set
				pfu.default = 1, pf.modified = %s, pf.modified_by = %s
			where
				pfu.user = %s and pf.name = pfu.parent and pf.company = %s and pf.name = %s
			""", (modified, user, user, company, pos_profile), auto_commit=1)
