# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
import six
from datetime import datetime
from frappe.model.document import Document
from frappe.email import sendmail_to_system_managers
from frappe.utils import add_days, add_years, nowdate, getdate, add_months, get_link_to_form
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

def get_member_based_on_subscription(subscription_id, email):
	members = frappe.get_all("Member", filters={
					'subscription_id': subscription_id,
					'email_id': email
				}, order_by="creation desc")
	return frappe.get_doc("Member", members[0]['name'])

@frappe.whitelist(allow_guest=True)
def trigger_razorpay_subscription(data):
	if isinstance(data, six.string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	subscription = data.payload.get("subscription", {}).get('entity', {})
	subscription = frappe._dict(subscription)

	payment = data.payload.get("payment", {}).get('entity', {})
	payment = frappe._dict(payment)

	try:
		data_json = json.dumps(data, indent=4, sort_keys=True)
		member = get_member_based_on_subscription(subscription.id, payment.email)
	except Exception as e:
		error_log = frappe.log_error(frappe.get_traceback() + '\n' + data_json , _("Membership Webhook Failed"))
		notify_failure(error_log)
		raise e

	if data.event == "subscription.activated":
		member.customer_id = payment.customer_id
	elif data.event == "subscription.charged":
		membership = frappe.new_doc("Membership")
		membership.update({
			"member": member.name,
			"membership_status": "Current",
			"membership_type": member.membership_type,
			"currency": "INR",
			"paid": 1,
			"payment_id": payment.id,
			"webhook_payload": data_json,
			"from_date": datetime.fromtimestamp(subscription.current_start),
			"to_date": datetime.fromtimestamp(subscription.current_end),
			"amount": payment.amount / 100 # Convert to rupees from paise
		})
		membership.insert(ignore_permissions=True)

	# Update these values anyway
	member.subscription_start = datetime.fromtimestamp(subscription.start_at)
	member.subscription_end = datetime.fromtimestamp(subscription.end_at)
	member.subscription_activated = 1
	member.save(ignore_permissions=True)

	return True



def notify_failure(log):
	try:
		content = """Dear System Manager,
Razorpay webhook for creating renewing membership subscription failed due to some reason. Please check the following error log linked below

Error Log: {0}

Regards,
Administrator""".format(get_link_to_form("Error Log", log.name))
		sendmail_to_system_managers("[Important] [ERPNext] Razorpay membership webhook failed , please check.", content)
	except:
		pass
