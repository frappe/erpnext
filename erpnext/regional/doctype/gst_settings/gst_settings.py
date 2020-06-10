# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, os
from frappe import _
from frappe.utils import get_url, nowdate, date_diff
from frappe.model.document import Document
from frappe.contacts.doctype.contact.contact import get_default_contact

class EmailMissing(frappe.ValidationError): pass

class GSTSettings(Document):
	def onload(self):
		data = frappe._dict()
		data.total_addresses = frappe.db.sql('''select count(*) from tabAddress where country = "India"''')
		data.total_addresses_with_gstin = frappe.db.sql('''select distinct count(*)
			from tabAddress where country = "India" and ifnull(gstin, '')!='' ''')
		self.set_onload('data', data)

@frappe.whitelist()
def send_reminder():
	frappe.has_permission('GST Settings', throw=True)

	last_sent = frappe.db.get_single_value('GST Settings', 'gstin_email_sent_on')
	if last_sent and date_diff(nowdate(), last_sent) < 3:
		frappe.throw(_("Please wait 3 days before resending the reminder."))

	frappe.db.set_value('GST Settings', 'GST Settings', 'gstin_email_sent_on', nowdate())

	# enqueue if large number of customers, suppliser
	frappe.enqueue('erpnext.regional.doctype.gst_settings.gst_settings.send_gstin_reminder_to_all_parties')
	frappe.msgprint(_('Email Reminders will be sent to all parties with email contacts'))

def send_gstin_reminder_to_all_parties():
	parties = []
	for address_name in frappe.db.sql('''select name
		from tabAddress where country = "India" and ifnull(gstin, '')='' '''):
		address = frappe.get_doc('Address', address_name[0])
		for link in address.links:
			party = frappe.get_doc(link.link_doctype, link.link_name)
			if link.link_doctype in ('Customer', 'Supplier'):
				t = (link.link_doctype, link.link_name, address.email_id)
				if not t in parties:
					parties.append(t)

	sent_to = []
	for party in parties:
		# get email from default contact
		try:
			email_id = _send_gstin_reminder(party[0], party[1], party[2], sent_to)
			sent_to.append(email_id)
		except EmailMissing:
			pass


@frappe.whitelist()
def send_gstin_reminder(party_type, party):
	'''Send GSTIN reminder to one party (called from Customer, Supplier form)'''
	frappe.has_permission(party_type, throw=True)
	email = _send_gstin_reminder(party_type ,party)
	if email:
		frappe.msgprint(_('Reminder to update GSTIN Sent'), title='Reminder sent', indicator='green')

def _send_gstin_reminder(party_type, party, default_email_id=None, sent_to=None):
	'''Send GST Reminder email'''
	email_id = frappe.db.get_value('Contact', get_default_contact(party_type, party), 'email_id')
	if not email_id:
		# get email from address
		email_id = default_email_id

	if not email_id:
		frappe.throw(_('Email not found in default contact'), exc=EmailMissing)

	if sent_to and email_id in sent_to:
		return

	frappe.sendmail(
		subject='Please update your GSTIN',
		recipients=email_id,
		message='''
		<p>Hello,</p>
		<p>Please help us send you GST Ready Invoices.</p>
		<p>
			<a href="{0}?party={1}">
			Click here to update your GSTIN Number in our system
			</a>
		</p>
		<p style="color: #aaa; font-size: 11px; margin-top: 30px;">
			Get your GST Ready ERP system at <a href="https://erpnext.com">https://erpnext.com</a>
			<br>
			ERPNext is a free and open source ERP system.
		</p>
		'''.format(os.path.join(get_url(), '/regional/india/update-gstin'), party)
	)

	return email_id
