# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import frappe.utils
from frappe import _
from erpnext.hr.doctype.daily_work_summary.daily_work_summary import get_employee_emails

class DailyWorkSummarySettings(Document):
	def validate(self):
		if self.companies:
			if not frappe.flags.in_test and not frappe.db.get_value('Email Account', dict(enable_incoming=1,
				default_incoming=1)):
				frappe.throw(_('There must be a default incoming Email Account enabled for this to work. Please setup a default incoming Email Account (POP/IMAP) and try again.'))

def trigger_emails():
	'''Send emails to Employees of the enabled companies at the give hour asking
	them what did they work on today'''
	settings = frappe.get_doc('Daily Work Summary Settings')
	for d in settings.companies:
		# if current hour
		if frappe.utils.nowtime().split(':')[0] == d.send_emails_at.split(':')[0]:
			emails = get_employee_emails(d.company)
			# find emails relating to a company
			if emails:
				daily_work_summary = frappe.get_doc(dict(doctype='Daily Work Summary',
					company=d.company)).insert()
				daily_work_summary.send_mails(settings, emails)

def send_summary():
	'''Send summary to everyone'''
	for d in frappe.get_all('Daily Work Summary', dict(status='Open')):
		daily_work_summary = frappe.get_doc('Daily Work Summary', d.name)
		daily_work_summary.send_summary()