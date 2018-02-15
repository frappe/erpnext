# # -*- coding: utf-8 -*-
# # Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import frappe.utils
from frappe import _

class DailyWorkSummarySetting(Document):
	def validate(self):
		if self.users:
			if not frappe.flags.in_test and not frappe.db.get_value('Email Account', dict(enable_incoming=1,
																						  default_incoming=1)):
				frappe.throw(_('There must be a default incoming Email Account enabled for this to work. Please setup a default incoming Email Account (POP/IMAP) and try again.'))

def trigger_emails():
	'''Send emails to Employees at the given hour asking
	them what did they work on today'''
	settings = frappe.get_all("Daily Work Summary Setting")
	for d in settings:
		setting_doc = frappe.get_doc("Daily Work Summary Setting", d)
		if is_current_hour(setting_doc.send_emails_at) and not is_holiday_today(setting_doc.holiday_list) and setting_doc.enabled:
			emails = [d.email for d in setting_doc.users]
			# find emails relating to a company
			if emails:
				daily_work_summary = frappe.get_doc(dict(doctype='Daily Work Summary',
														 setting=setting_doc.name)).insert()
				daily_work_summary.send_mails(setting_doc, emails)

def is_current_hour(hour):
	return frappe.utils.nowtime().split(':')[0] == hour.split(':')[0]

def is_holiday_today(holiday_list):
	date = frappe.utils.today()
	if holiday_list:
		return frappe.get_all('Holiday List', dict(name=holiday_list, holiday_date=date)) and True or False
	else:
		return False

def send_summary():
	'''Send summary to everyone'''
	for d in frappe.get_all('Daily Work Summary', dict(status='Open')):
		daily_work_summary = frappe.get_doc('Daily Work Summary', d.name)
		daily_work_summary.send_summary()