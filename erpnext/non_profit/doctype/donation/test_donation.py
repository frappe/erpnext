# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import json
from frappe.integrations.utils import make_post_request
from frappe.utils.data import get_url
from erpnext.non_profit.doctype.donation.donation import create_donation

class TestDonation(unittest.TestCase):
	def setUp(self):
		create_donor_type()
		settings = frappe.get_doc('Non Profit Settings')
		settings.company = '_Test Company'
		settings.donation_company = '_Test Company'
		settings.default_donor_type = '_Test Donor'
		settings.automate_donation_payment_entries = 1
		settings.donation_debit_account = 'Debtors - _TC'
		settings.donation_payment_account =  'Cash - _TC'
		settings.flags.ignore_permissions = True
		settings.save()

	def test_donation_webhook(self):
		request_data = get_request_data()
		data = json.dumps(request_data)
		url = get_url() + '/api/method/erpnext.non_profit.doctype.donation.donation.capture_razorpay_donations'
		make_post_request(url=url, data=data)

		self.assertTrue(frappe.db.exists('Donor', 'test@12345.com'))
		self.assertTrue(frappe.db.exists('Donation', {
			'razorpay_payment_id': request_data.get('payload').get('payment').get('entity').get('id')
		}))

	def test_payment_entry_for_donations(self):
		donor = create_donor()
		create_mode_of_payment()
		payment = frappe._dict({
			'amount': 100,
			'method': 'Debit Card',
			'id': 'pay_MeXAmsgeKOhq7O'
		})
		donation = create_donation(donor, payment)

		self.assertTrue(donation.name)

		# Naive test to check if at all payment entry is generated
		# This method is actually triggered from Payment Gateway
		# In any case if details were missing, this would throw an error
		donation.on_payment_authorized()
		donation.reload()

		self.assertEquals(donation.paid, 1)
		self.assertTrue(frappe.db.exists('Payment Entry', {'reference_no': donation.name}))



def get_request_data():
	return {
	'entity': 'event',
	'account_id': 'acc_GcYX2ikQ4TBiL2',
	'event': 'payment.captured',
	'contains': [
		'payment'
	],
	'payload': {
		'payment': {
			'entity': {
				'id': 'pay_GeXAmsgeKOhq7O',
				'entity': 'payment',
				'amount': 100,
				'currency': 'INR',
				'status': 'captured',
				'order_id': 'order_GeXAcscNqaIJpy',
				'method': 'upi',
				'amount_refunded': 0,
				'captured': 'true',
				'description': 'null',
				'vpa': 'test@okhdfcbank',
				'email': 'test@12345.com',
				'contact': '+1234567890',
				'notes': {
					'full_name': '_Test RazorPay Donor',
					'email': 'par@12345.com',
					'phone': '1987788987'
				},
				'fee': 2,
				'tax': 0,
				'created_at': 1613978215
			}
		}
	},
	'created_at': 1613978215
}


def create_donor_type():
	if not frappe.db.exists('Donor Type', '_Test Donor'):
		frappe.get_doc({
			'doctype': 'Donor Type',
			'donor_type': '_Test Donor'
		}).insert()


def create_donor():
	donor = frappe.db.exists('Donor', 'donor@test.com')
	if donor:
		return frappe.get_doc('Donor', 'donor@test.com')
	else:
		return frappe.get_doc({
			'doctype': 'Donor',
			'donor_name': '_Test Donor',
			'donor_type': '_Test Donor',
			'email': 'donor@test.com'
		}).insert()


def create_mode_of_payment():
	if not frappe.db.exists('Mode of Payment', 'Debit Card'):
		frappe.get_doc({
			'doctype': 'Mode of Payment',
			'mode_of_payment': 'Debit Card',
			'accounts': [{
				'company': '_Test Company',
				'default_account': 'Cash - _TC'
			}]
		}).insert()