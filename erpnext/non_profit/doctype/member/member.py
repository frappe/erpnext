# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import cint
from frappe.integrations.utils import get_payment_gateway_controller

class Member(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)


	def validate(self):
		if self.email:
			self.validate_email_type(self.email)
		if self.email_id:
			self.validate_email_type(self.email_id)

	def validate_email_type(self, email):
		from frappe.utils import validate_email_address
		validate_email_address(email.strip(), True)

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

def get_or_create_member(user_details):
	member_list = frappe.get_all("Member", filters={'email': user_details.email, 'membership_type': user_details.plan_id})
	if member_list and member_list[0]:
		return member_list[0]['name']
	else:
		return create_member(user_details)

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
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("Contact Creation Failed"))
		pass

	return customer.name

@frappe.whitelist(allow_guest=True)
def create_member_subscription_order(user_details):
	"""Create Member subscription and order for payment

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
	member = get_or_create_member(user_details)
	if not member:
		member = create_member(user_details)

	subscription = member.setup_subscription()

	member.subscription_id = subscription.get('subscription_id')
	member.save(ignore_permissions=True)

	return subscription