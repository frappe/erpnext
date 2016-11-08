# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import frappe.utils

class DailyWorkSummarySettings(Document):
	pass

def trigger_emails():
	settings = frappe.get_doc('Daily Work Summary Settings')
	for d in settings.companies:
		# if current hour
		if frappe.utils.nowtime().split(':')[0] == d.send_emails_at.split(':')[0]:
			work_summary = frappe.get_doc(dict(doctype='Daily Work Summary',
				company=d.company)).insert()
			work_summary.send_mails(settings)