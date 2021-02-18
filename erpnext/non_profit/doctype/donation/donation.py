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
	def on_payment_authorized(self, *args, **kwargs):
		self.load_from_db()
		self.db_set('paid', 1)


@frappe.whitelist(allow_guest=True)
def capture_razorpay_donations(*args, **kwargs):
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

		donor = get_donor(payment.email)
		if not donor:
			donor = create_donor(payment)

		create_donation(donor, payment)

	except Exception as e:
		message = '{0}\n\n{1}\n\n{2}: {3}'.format(e, frappe.get_traceback(), _('Payment ID'), payment.id)
		log = frappe.log_error(message, _('Error creating donation entry for {0}').format(donor.name))
		notify_failure(log)
		return { 'status': 'Failed', 'reason': e }

	return { 'status': 'Success' }


def create_donation(donor, payment):
	if not frappe.db.exists('Mode of Payment', payment.method):
		create_mode_of_payment(payment.method)

	donation = frappe.new_doc('Donation')
	donation.update({
		'donor': donor.name,
		'donor_name': donor.donor_name,
		'email': donor.email,
		'date': getdate(),
		'amount': flt(payment.amount),
		'mode_of_payment': payment.method,
		'razorpay_payment_id': payment.id
	})

	donation.insert(ignore_permissions=True)


def get_donor(email):
	donors = frappe.get_all('Donor',
		filters={'email': email},
		order_by='creation desc')

	try:
		return frappe.get_doc('Donor', donors[0]['name'])
	except:
		return None


@frappe.whitelist()
def create_donor(payment):
	donor_details = frappe._dict(payment)

	donor = frappe.new_doc('Donor')
	donor.update({
		'donor_name': donor_details.email,
		'email': donor_details.email,
		'contact': donor_details.contact
	})

	if donor_details.get('notes'):
		donor = get_additional_notes(donor, donor_details)

	donor.insert(ignore_mandatory=True, ignore_permissions=True)
	return donor


def get_additional_notes(donor, donor_details):
	if type(donor_details.notes) == dict:
		for k, v in donor_details.notes.items():
			notes = '\n'.join('{}: {}'.format(k, v))

			# extract donor name from notes
			if 'name' in k.lower():
				donor.update({
					'donor_name': donor_details.notes.get(k)
				})

		donor.add_comment('Comment', notes)

	elif type(donor_details.notes) == str:
		donor.add_comment('Comment', donor_details.notes)

	return donor


def create_mode_of_payment(method):
	frappe.get_doc({
		'doctype': 'Mode of Payment',
		'mode_of_payment': method
	}).insert(ignore_permissions=True, ignore_mandatory=True)


def notify_failure(log):
	try:
		content = _('''
			Dear System Manager,
			Razorpay webhook for creating donation failed due to some reason.
			Please check the error log linked below
			Error Log: {0}
			Regards, Administrator
		''').format(get_link_to_form('Error Log', log.name))

		sendmail_to_system_managers(_('[Important] [ERPNext] Razorpay donation webhook failed, please check.'), content)
	except:
		pass

