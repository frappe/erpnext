# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import datetime

import frappe
import six
from frappe import _
from frappe.email import sendmail_to_system_managers
from frappe.model.document import Document
from frappe.utils import add_days, add_months, add_years, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.non_profit.doctype.member.member import create_member


class Membership(Document):
	def validate(self):
		if not self.member or not frappe.db.exists("Member", self.member):
			# for web forms
			user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
			if user_type == "Website User":
				self.create_member_from_website_user()
			else:
				frappe.throw(_("Please select a Member"))

		self.validate_membership_period()

	def create_member_from_website_user(self):
		member_name = frappe.get_value("Member", dict(email_id=frappe.session.user))

		if not member_name:
			user = frappe.get_doc("User", frappe.session.user)
			member = frappe.get_doc(dict(
				doctype="Member",
				email_id=frappe.session.user,
				membership_type=self.membership_type,
				member_name=user.get_fullname()
			)).insert(ignore_permissions=True)
			member_name = member.name

		if self.get("__islocal"):
			self.member = member_name

	def validate_membership_period(self):
		# get last membership (if active)
		last_membership = erpnext.get_last_membership(self.member)

		# if person applied for offline membership
		if last_membership and last_membership.name != self.name and not frappe.session.user == "Administrator":
			# if last membership does not expire in 30 days, then do not allow to renew
			if getdate(add_days(last_membership.to_date, -30)) > getdate(nowdate()) :
				frappe.throw(_("You can only renew if your membership expires within 30 days"))

			self.from_date = add_days(last_membership.to_date, 1)
		elif frappe.session.user == "Administrator":
			self.from_date = self.from_date
		else:
			self.from_date = nowdate()

		if frappe.db.get_single_value("Non Profit Settings", "billing_cycle") == "Yearly":
			self.to_date = add_years(self.from_date, 1)
		else:
			self.to_date = add_months(self.from_date, 1)

	def on_payment_authorized(self, status_changed_to=None):
		if status_changed_to not in ("Completed", "Authorized"):
			return
		self.load_from_db()
		self.db_set("paid", 1)
		settings = frappe.get_doc("Non Profit Settings")
		if settings.allow_invoicing and settings.automate_membership_invoicing:
			self.generate_invoice(with_payment_entry=settings.automate_membership_payment_entries, save=True)


	@frappe.whitelist()
	def generate_invoice(self, save=True, with_payment_entry=False):
		if not (self.paid or self.currency or self.amount):
			frappe.throw(_("The payment for this membership is not paid. To generate invoice fill the payment details"))

		if self.invoice:
			frappe.throw(_("An invoice is already linked to this document"))

		member = frappe.get_doc("Member", self.member)
		if not member.customer:
			frappe.throw(_("No customer linked to member {0}").format(frappe.bold(self.member)))

		plan = frappe.get_doc("Membership Type", self.membership_type)
		settings = frappe.get_doc("Non Profit Settings")
		self.validate_membership_type_and_settings(plan, settings)

		invoice = make_invoice(self, member, plan, settings)
		self.reload()
		self.invoice = invoice.name

		if with_payment_entry:
			self.make_payment_entry(settings, invoice)

		if save:
			self.save()

		return invoice

	def validate_membership_type_and_settings(self, plan, settings):
		settings_link = get_link_to_form("Membership Type", self.membership_type)

		if not settings.membership_debit_account:
			frappe.throw(_("You need to set <b>Debit Account</b> in {0}").format(settings_link))

		if not settings.company:
			frappe.throw(_("You need to set <b>Default Company</b> for invoicing in {0}").format(settings_link))

		if not plan.linked_item:
			frappe.throw(_("Please set a Linked Item for the Membership Type {0}").format(
				get_link_to_form("Membership Type", self.membership_type)))

	def make_payment_entry(self, settings, invoice):
		if not settings.membership_payment_account:
			frappe.throw(_("You need to set <b>Payment Account</b> for Membership in {0}").format(
				get_link_to_form("Non Profit Settings", "Non Profit Settings")))

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		frappe.flags.ignore_account_permission = True
		pe = get_payment_entry(dt="Sales Invoice", dn=invoice.name, bank_amount=invoice.grand_total)
		frappe.flags.ignore_account_permission=False
		pe.paid_to = settings.membership_payment_account
		pe.reference_no = self.name
		pe.reference_date = getdate()
		pe.flags.ignore_mandatory = True
		pe.save()
		pe.submit()

	@frappe.whitelist()
	def send_acknowlement(self):
		settings = frappe.get_doc("Non Profit Settings")
		if not settings.send_email:
			frappe.throw(_("You need to enable <b>Send Acknowledge Email</b> in {0}").format(
				get_link_to_form("Non Profit Settings", "Non Profit Settings")))

		member = frappe.get_doc("Member", self.member)
		if not member.email_id:
			frappe.throw(_("Email address of member {0} is missing").format(frappe.utils.get_link_to_form("Member", self.member)))

		plan = frappe.get_doc("Membership Type", self.membership_type)
		email = member.email_id
		attachments = [frappe.attach_print("Membership", self.name, print_format=settings.membership_print_format)]

		if self.invoice and settings.send_invoice:
			attachments.append(frappe.attach_print("Sales Invoice", self.invoice, print_format=settings.inv_print_format))

		email_template = frappe.get_doc("Email Template", settings.email_template)
		context = { "doc": self, "member": member}

		email_args = {
			"recipients": [email],
			"message": frappe.render_template(email_template.get("response"), context),
			"subject": frappe.render_template(email_template.get("subject"), context),
			"attachments": attachments,
			"reference_doctype": self.doctype,
			"reference_name": self.name
		}

		if not frappe.flags.in_test:
			frappe.enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)
		else:
			frappe.sendmail(**email_args)

	def generate_and_send_invoice(self):
		self.generate_invoice(save=False)
		self.send_acknowlement()


def make_invoice(membership, member, plan, settings):
	invoice = frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": member.customer,
		"debit_to": settings.membership_debit_account,
		"currency": membership.currency,
		"company": settings.company,
		"is_pos": 0,
		"items": [
			{
				"item_code": plan.linked_item,
				"rate": membership.amount,
				"qty": 1
			}
		]
	})
	invoice.set_missing_values()
	invoice.insert()
	invoice.submit()

	frappe.msgprint(_("Sales Invoice created successfully"))

	return invoice


def get_member_based_on_subscription(subscription_id, email=None, customer_id=None):
	filters = {"subscription_id": subscription_id}
	if email:
		filters.update({"email_id": email})
	if customer_id:
		filters.update({"customer_id": customer_id})

	members = frappe.get_all("Member", filters=filters, order_by="creation desc")

	try:
		return frappe.get_doc("Member", members[0]["name"])
	except Exception:
		return None


def verify_signature(data, endpoint="Membership"):
	signature = frappe.request.headers.get("X-Razorpay-Signature")

	settings = frappe.get_doc("Non Profit Settings")
	key = settings.get_webhook_secret(endpoint)

	controller = frappe.get_doc("Razorpay Settings")

	controller.verify_signature(data, signature, key)
	frappe.set_user(settings.creation_user)


@frappe.whitelist(allow_guest=True)
def trigger_razorpay_subscription(*args, **kwargs):
	data = frappe.request.get_data(as_text=True)
	data = process_request_data(data)

	subscription = data.payload.get("subscription", {}).get("entity", {})
	subscription = frappe._dict(subscription)

	payment = data.payload.get("payment", {}).get("entity", {})
	payment = frappe._dict(payment)

	try:
		if not data.event == "subscription.charged":
			return

		member = get_member_based_on_subscription(subscription.id, payment.email)
		if not member:
			member = create_member(frappe._dict({
				"fullname": payment.email,
				"email": payment.email,
				"plan_id": get_plan_from_razorpay_id(subscription.plan_id)
			}))

			member.subscription_id = subscription.id
			member.customer_id = payment.customer_id

			if subscription.get("notes"):
				member = get_additional_notes(member, subscription)

		company = get_company_for_memberships()
		# Update Membership
		membership = frappe.new_doc("Membership")
		membership.update({
			"company": company,
			"member": member.name,
			"membership_status": "Current",
			"membership_type": member.membership_type,
			"currency": "INR",
			"paid": 1,
			"payment_id": payment.id,
			"from_date": datetime.fromtimestamp(subscription.current_start),
			"to_date": datetime.fromtimestamp(subscription.current_end),
			"amount": payment.amount / 100 # Convert to rupees from paise
		})
		membership.flags.ignore_mandatory = True
		membership.insert()

		# Update membership values
		member.subscription_start = datetime.fromtimestamp(subscription.start_at)
		member.subscription_end = datetime.fromtimestamp(subscription.end_at)
		member.subscription_status = "Active"
		member.flags.ignore_mandatory = True
		member.save()

		settings = frappe.get_doc("Non Profit Settings")
		if settings.allow_invoicing and settings.automate_membership_invoicing:
			membership.reload()
			membership.generate_invoice(with_payment_entry=settings.automate_membership_payment_entries, save=True)

	except Exception as e:
		message = "{0}\n\n{1}\n\n{2}: {3}".format(e, frappe.get_traceback(), _("Payment ID"), payment.id)
		log = frappe.log_error(message, _("Error creating membership entry for {0}").format(member.name))
		notify_failure(log)
		return {"status": "Failed", "reason": e}

	return {"status": "Success"}


@frappe.whitelist(allow_guest=True)
def update_halted_razorpay_subscription(*args, **kwargs):
	"""
	When all retries have been exhausted, Razorpay moves the subscription to the halted state.
	The customer has to manually retry the charge or change the card linked to the subscription,
	for the subscription to move back to the active state.
	"""
	if frappe.request:
		data = frappe.request.get_data(as_text=True)
		data = process_request_data(data)
	elif frappe.flags.in_test:
		data = kwargs.get("data")
		data = frappe._dict(data)
	else:
		return

	if not data.event == "subscription.halted":
		return

	subscription = data.payload.get("subscription", {}).get("entity", {})
	subscription = frappe._dict(subscription)

	try:
		member = get_member_based_on_subscription(subscription.id, customer_id=subscription.customer_id)
		if not member:
			frappe.throw(_("Member with Razorpay Subscription ID {0} not found").format(subscription.id))

		member.subscription_status = "Halted"
		member.flags.ignore_mandatory = True
		member.save()

		if subscription.get("notes"):
			member = get_additional_notes(member, subscription)

	except Exception as e:
		message = "{0}\n\n{1}".format(e, frappe.get_traceback())
		log = frappe.log_error(message, _("Error updating halted status for member {0}").format(member.name))
		notify_failure(log)
		return {"status": "Failed", "reason": e}

	return {"status": "Success"}


def process_request_data(data):
	try:
		verify_signature(data)
	except Exception as e:
		log = frappe.log_error(e, "Membership Webhook Verification Error")
		notify_failure(log)
		return {"status": "Failed", "reason": e}

	if isinstance(data, six.string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	return data


def get_company_for_memberships():
	company = frappe.db.get_single_value("Non Profit Settings", "company")
	if not company:
		from erpnext.non_profit.utils import get_company
		company = get_company()
	return company


def get_additional_notes(member, subscription):
	if type(subscription.notes) == dict:
		for k, v in subscription.notes.items():
			notes = "\n".join("{}: {}".format(k, v))

			# extract member name from notes
			if "name" in k.lower():
				member.update({
					"member_name": subscription.notes.get(k)
				})

			# extract pan number from notes
			if "pan" in k.lower():
				member.update({
					"pan_number": subscription.notes.get(k)
				})

		member.add_comment("Comment", notes)

	elif type(subscription.notes) == str:
		member.add_comment("Comment", subscription.notes)

	return member


def notify_failure(log):
	try:
		content = """
			Dear System Manager,
			Razorpay webhook for creating renewing membership subscription failed due to some reason.
			Please check the following error log linked below
			Error Log: {0}
			Regards, Administrator
		""".format(get_link_to_form("Error Log", log.name))

		sendmail_to_system_managers("[Important] [ERPNext] Razorpay membership webhook failed , please check.", content)
	except Exception:
		pass


def get_plan_from_razorpay_id(plan_id):
	plan = frappe.get_all("Membership Type", filters={"razorpay_plan_id": plan_id}, order_by="creation desc")

	try:
		return plan[0]["name"]
	except Exception:
		return None


def set_expired_status():
	frappe.db.sql("""
		UPDATE
			`tabMembership` SET `status` = 'Expired'
		WHERE
			`status` not in ('Cancelled') AND `to_date` < %s
		""", (nowdate()))
