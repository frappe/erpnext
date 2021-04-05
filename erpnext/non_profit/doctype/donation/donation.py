# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import six
import json
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, flt, get_link_to_form
from frappe.email import sendmail_to_system_managers
from erpnext.non_profit.doctype.membership.membership import verify_signature

class Donation(Document):
	def validate(self):
		if not self.donor or not frappe.db.exists('Donor', self.donor):
			# for web forms
			user_type = frappe.db.get_value('User', frappe.session.user, 'user_type')
			if user_type == 'Website User':
				self.create_donor_for_website_user()
			else:
				frappe.throw(_('Please select a Member'))

	def create_donor_for_website_user(self):
		donor_name = frappe.get_value('Donor', dict(email=frappe.session.user))

		if not donor_name:
			user = frappe.get_doc('User', frappe.session.user)
			donor = frappe.get_doc(dict(
				doctype='Donor',
				donor_type=self.get('donor_type'),
				email=frappe.session.user,
				member_name=user.get_fullname()
			)).insert(ignore_permissions=True)
			donor_name = donor.name

		if self.get('__islocal'):
			self.donor = donor_name

	def on_payment_authorized(self, *args, **kwargs):
		self.load_from_db()
		self.create_payment_entry()

	def create_payment_entry(self, date=None):
		settings = frappe.get_doc('Non Profit Settings')
		if not settings.automate_donation_payment_entries:
			return

		if not settings.donation_payment_account:
			frappe.throw(_('You need to set <b>Payment Account</b> for Donation in {0}').format(
				get_link_to_form('Non Profit Settings', 'Non Profit Settings')))

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		frappe.flags.ignore_account_permission = True
		pe = get_payment_entry(dt=self.doctype, dn=self.name)
		frappe.flags.ignore_account_permission = False
		pe.paid_from = settings.donation_debit_account
		pe.paid_to = settings.donation_payment_account
		pe.posting_date = date or getdate()
		pe.reference_no = self.name
		pe.reference_date = date or getdate()
		pe.flags.ignore_mandatory = True
		pe.insert()
		pe.submit()


@frappe.whitelist(allow_guest=True)
def capture_razorpay_donations(*args, **kwargs):
	"""
		Creates Donation from Razorpay Webhook Request Data on payment.captured event
		Creates Donor from email if not found
	"""
	data = frappe.request.get_data(as_text=True)

	try:
		verify_signature(data, endpoint='Donation')
	except Exception as e:
		log = frappe.log_error(e, 'Donation Webhook Verification Error')
		notify_failure(log)
		return { 'status': 'Failed', 'reason': e }

	if isinstance(data, six.string_types):
		data = json.loads(data)
	data = frappe._dict(data)

	payment = data.payload.get('payment', {}).get('entity', {})
	payment = frappe._dict(payment)

	try:
		if not data.event == 'payment.captured':
			return

		# to avoid capturing subscription payments as donations
		if payment.description and 'subscription' in str(payment.description).lower():
			return

		donor = get_donor(payment.email)
		if not donor:
			donor = create_donor(payment)

		donation = create_donation(donor, payment)
		donation.run_method('create_payment_entry')

	except Exception as e:
		message = '{0}\n\n{1}\n\n{2}: {3}'.format(e, frappe.get_traceback(), _('Payment ID'), payment.id)
		log = frappe.log_error(message, _('Error creating donation entry for {0}').format(donor.name))
		notify_failure(log)
		return { 'status': 'Failed', 'reason': e }

	return { 'status': 'Success' }


def create_donation(donor, payment):
	if not frappe.db.exists('Mode of Payment', payment.method):
		create_mode_of_payment(payment.method)

	company = get_company_for_donations()
	donation = frappe.get_doc({
		'doctype': 'Donation',
		'company': company,
		'donor': donor.name,
		'donor_name': donor.donor_name,
		'email': donor.email,
		'date': getdate(),
		'amount': flt(payment.amount) / 100, # Convert to rupees from paise
		'mode_of_payment': payment.method,
		'razorpay_payment_id': payment.id
	}).insert(ignore_mandatory=True)

	donation.submit()
	return donation


def get_donor(email):
	donors = frappe.get_all('Donor',
		filters={'email': email},
		order_by='creation desc')

	try:
		return frappe.get_doc('Donor', donors[0]['name'])
	except Exception:
		return None


@frappe.whitelist()
def create_donor(payment):
	donor_details = frappe._dict(payment)
	donor_type = frappe.db.get_single_value('Non Profit Settings', 'default_donor_type')

	donor = frappe.new_doc('Donor')
	donor.update({
		'donor_name': donor_details.email,
		'donor_type': donor_type,
		'email': donor_details.email,
		'contact': donor_details.contact
	})

	if donor_details.get('notes'):
		donor = get_additional_notes(donor, donor_details)

	donor.insert(ignore_mandatory=True)
	return donor


def get_company_for_donations():
	company = frappe.db.get_single_value('Non Profit Settings', 'donation_company')
	if not company:
		from erpnext.healthcare.setup import get_company
		company = get_company()
	return company


def get_additional_notes(donor, donor_details):
	if type(donor_details.notes) == dict:
		for k, v in donor_details.notes.items():
			notes = '\n'.join('{}: {}'.format(k, v))

			# extract donor name from notes
			if 'name' in k.lower():
				donor.update({
					'donor_name': donor_details.notes.get(k)
				})

			# extract pan from notes
			if 'pan' in k.lower():
				donor.update({
					'pan_number': donor_details.notes.get(k)
				})

		donor.add_comment('Comment', notes)

	elif type(donor_details.notes) == str:
		donor.add_comment('Comment', donor_details.notes)

	return donor


def create_mode_of_payment(method):
	frappe.get_doc({
		'doctype': 'Mode of Payment',
		'mode_of_payment': method
	}).insert(ignore_mandatory=True)


def notify_failure(log):
	try:
		content = '''
			Dear System Manager,
			Razorpay webhook for creating donation failed due to some reason.
			Please check the error log linked below
			Error Log: {0}
			Regards, Administrator
		'''.format(get_link_to_form('Error Log', log.name))

		sendmail_to_system_managers(_('[Important] [ERPNext] Razorpay donation webhook failed, please check.'), content)
	except Exception:
		pass

