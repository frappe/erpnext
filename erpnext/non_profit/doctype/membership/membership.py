# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, nowdate, getdate, add_months, cint
from frappe.integrations.utils import get_payment_gateway_controller
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

		if frappe.db.get_single_value("Membership Settings", "billing_cycle") == "Yearly":
			self.to_date = add_years(self.from_date, 1)
		else:
			self.to_date = add_months(self.from_date, 1)

	def on_payment_authorized(self, status_changed_to=None):
		if status_changed_to in ("Completed", "Authorized"):
			self.load_from_db()
			self.db_set('paid', 1)

	def setup_subscription(self):
		membership_settings = frappe.get_doc("Membership Settings")
		if not membership_settings.enable_razorpay:
			frappe.throw("Please enable Razorpay to setup subscription")

		controller = get_payment_gateway_controller("Razorpay")
		settings = controller.get_settings({})

		plan_id = frappe.get_value("Membership Type", self.membership_type, "razorpay_plan_id")

		if not plan_id:
			frappe.throw(_("Please setup Razorpay Plan ID"))

		subscription_details = {
			"plan_id": plan_id,
			"billing_frequency": cint(membership_settings.billing_frequency),
			"customer_notify": 1
		}

		args = {
			'subscription_details': subscription_details
		}

		subscription = controller.setup_subscription(settings, **args)

		return subscription


def get_member_if_exists(email, plan):
	member_list = frappe.get_all("Member", filters={'email': email, 'membership_type': plan})
	if member_list and member_list[0]:
		return member_list[0]['name']
	else:
		return None

def create_member(user_details):
	member = frappe.new_doc("Member")
	member.update({
		"member_name": user_details.fullname,
		"email_id": user_details.email,
		"pan_number": user_details.pan,
		"membership_type": user_details.plan_id,
		"customer": create_customer(user_details)
	})

	member.insert(ignore_permissions=True)
	return member

def create_customer(user_details):
	customer = frappe.new_doc("Customer")
	customer.customer_name = user_details.fullname
	customer.customer_type = "Individual"
	customer.insert(ignore_permissions=True)

	try:
		contact = frappe.new_doc("Contact")
		contact.first_name = user_details.fullname
		contact.add_phone(user_details.mobile, is_primary_phone=1, is_primary_mobile_no=1)
		contact.add_email(user_details.email, is_primary=1)
		contact.insert(ignore_permissions=True)

		contact.append("links", {
			"link_doctype": "Customer",
			"link_name": customer.name
		})

		contact.insert()
	except Exception:
		error_log = frappe.log_error(frappe.get_traceback(), _("Contact Creation Failed"))

	return customer.name

def create_membership(member, plan):
	membership = frappe.new_doc("Membership")
	membership.update({
		"member": member.name,
		"membership_status": "New",
		"membership_type": member.membership_type,
		"currency": "INR",
		"amount": plan.amount,
		"from_date": getdate()
	})

	membership.insert(ignore_permissions=True)

	return membership

@frappe.whitelist(allow_guest=True)
def create_membership_subscription(user_details):
	"""Summary

	Args:
	    user_details (TYPE): Description

	Returns:
	    Dictionary: Dictionary with subscription details
	    {
	    	'subscription_details': {
	    								'plan_id': 'plan_EXwyxDYDCj3X4v',
							  			'billing_frequency': 24,
							  			'customer_notify': 1
							  		},
			'subscription_id': 'sub_EZycCvXFvqnC6p'
		}
	"""
	# {"plan_id":"IFF Starter","fullname":"Shivam Mishra","mobile":"7506056962","email":"shivam@shivam.dev","pan":"Testing123"}
	user_details = frappe._dict(user_details)
	member = get_member_if_exists(user_details.email, user_details.plan_id)
	plan = frappe.get_doc("Membership Type", user_details.plan_id)
	if not member:
		member = create_member(user_details)

	membership = create_membership(member, plan)

	return membership.setup_subscription()

@frappe.whitelist(allow_guest=True)
def razorpay_subscription_started(data={}):
	data = {
			"entity": "event",
			"event": "subscription.activated",
			"payload": {
				"subscription": {
					"entity": {
						"id": "sub_EZZsbKwt5xRYH6",
						"entity": "subscription",
						"plan_id": "plan_EXwyxDYDCj3X4v",
						"customer_id": "cust_EZZw80dUQgID8C",
						"current_start": 1585822073,
						"current_end": 1588357800,
						"start_at": 1585822073,
						"end_at": 1646159400,
						"auth_attempts": 0,
						"total_count": 24,
						"paid_count": 1,
					}
				},
				"payment": {
					"entity": {
						"id": "pay_EZZw7v9NEUFCVJ",
						"amount": 10000,
						"currency": "INR",
						"method": "card",
					}
				}
			},
			"created_at": 1585822079
		}
	data = frappe._dict(data)

	pass