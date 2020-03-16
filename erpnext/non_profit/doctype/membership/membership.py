# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, nowdate, getdate
from frappe import _
import erpnext


class Membership(Document):
	def validate(self):
		if not self.member or not frappe.db.exists("Member", self.member):
			member_name = frappe.get_value('Member', dict(email=frappe.session.user))

			if not member_name:
				user = frappe.get_doc('User', frappe.session.user)
				member = frappe.get_doc(dict(
					doctype='Member',
					email=frappe.session.user,
					membership_type=self.membership_type,
					member_name=user.get_fullname()
				)).insert(ignore_permissions=True)
				member_name = member.name

			if self.get("__islocal"):
				self.member = member_name

		# get last membership (if active)
		last_membership = erpnext.get_last_membership()

		# if person applied for offline membership
		if last_membership and not frappe.session.user == "Administrator":
			# if last membership does not expire in 30 days, then do not allow to renew
			if getdate(add_days(last_membership.to_date, -30)) > getdate(nowdate()) :
				frappe.throw(_('You can only renew if your membership expires within 30 days'))

			self.from_date = add_days(last_membership.to_date, 1)
		elif frappe.session.user == "Administrator":
			self.from_date = self.from_date
		else:
			self.from_date = nowdate()

		self.to_date = add_years(self.from_date, 1)

	def on_payment_authorized(self, status_changed_to=None):
		if status_changed_to in ("Completed", "Authorized"):
			self.load_from_db()
			self.db_set('paid', 1)

@frappe.whitelist()
def create_membership(name, email, membership_type, from_date, to_date, currency, amount, paid):
	member = get_or_create_member_using_email(email, name, membership_type)

	membership = frappe.new_doc("Membership")
	membership.membership_type = membership_type
	membership.from_date = from_date
	membership.to_date = to_date
	membership.currency = currency
	membership.amount = amount
	membership.paid = paid

	membership.insert()

	return membership.as_json()

def get_or_create_member_using_email(email, name, membership_type):
	member_list = frappe.get_all("Member", filters={'email': email})
	if len(member_list):
		return member_list[0]['name']
	else:
		new_member = frappe.new_doc('Member')
		new_member.member_name = name
		new_member.membership_type = membership_type
		new_member.email = email
		new_member.insert()
		new_member.load_from_db()

		return new_member.name

