# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import frappe.utils

# test_records = frappe.get_test_records('Daily Work Summary')

class TestDailyWorkSummary(unittest.TestCase):
	def test_email_trigger(self):
		settings, employees, emails = self.setup_and_prepare_test(frappe.utils.nowtime().split(':')[0])

		for d in employees:
			# check that email is sent to this employee
			self.assertTrue(d.user_id in [d.recipient for d in emails
				if settings.subject in d.message])

	def test_email_trigger_failed(self):
		hour = '00'
		if frappe.utils.nowtime().split(':')[0]=='00':
			hour = '01'

		settings, employees, emails = self.setup_and_prepare_test(hour)

		for d in employees:
			# check that email is sent to this employee
			self.assertFalse(d.user_id in [d.recipient for d in emails
				if settings.subject in d.message])

	def test_summary(self):
		pass

	def setup_and_prepare_test(self, hour):
		frappe.db.sql('delete from `tabEmail Queue`')

		# setup email to trigger at this our
		settings = frappe.get_doc('Daily Work Summary Settings')
		settings.companies = []

		settings.append('companies', dict(company='_Test Company',
			send_emails_at=hour + ':00'))
		settings.test_subject = 'this is a subject for testing summary emails'
		settings.save()

		from erpnext.hr.doctype.daily_work_summary_settings.daily_work_summary_settings \
			import trigger_emails
		trigger_emails()

		# check if emails are created
		employees = frappe.get_all('Employee', fields = ['user_id'],
			filters=dict(company='_Test Company', status='Active'))

		emails = frappe.get_all('Email Queue', fields=['recipient', 'message'])

		return settings, employees, emails